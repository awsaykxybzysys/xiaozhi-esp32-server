#include "ai_agent.h"
#include "board.h"
#include <esp_log.h>
#include <esp_timer.h>
#include <esp_task_wdt.h>
#include <inttypes.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <cJSON.h>
#include <cstring>
#include <sstream>
#include <algorithm>

#define TAG "AiAgent"

AiAgent::AiAgent() : is_processing_(false), should_stop_(false), processing_task_handle_(NULL) {
    // ESP_LOGI(TAG, "AI Agent initialized with Dify API");
}

AiAgent::~AiAgent() {
    StopStreaming();
}

bool AiAgent::StartStreamingChat(
    const std::string& query,
    const std::vector<FileInfo>& files,
    const std::string& conversation_id,
    const std::string& user_id,
    StreamCallback callback) {
    
    if (is_processing_.load()) {
        // ESP_LOGW(TAG, "AI Agent is already processing");
        if (callback) {
            callback("", false, "AI服务正在处理中，请稍后再试");
        }
        return false;
    }
    
    if (query.empty()) {
        // ESP_LOGE(TAG, "Query cannot be empty");
        if (callback) {
            callback("", false, "查询内容不能为空");
        }
        return false;
    }
    
    should_stop_ = false;
    is_processing_ = true;
    
    // 保存对话ID
    {
        std::lock_guard<std::mutex> lock(conversation_mutex_);
        current_conversation_id_ = conversation_id;
    }
    
    // ESP_LOGI(TAG, "Starting streaming chat with query: %s", query.c_str());
    
    // 使用FreeRTOS任务而不是std::thread，可以更好地控制栈大小
    auto* task_data = new AiAgent::StreamingTaskData;
    task_data->agent = this;
    task_data->query = query;
    task_data->files_ptr = new std::vector<FileInfo>(files);
    task_data->conversation_id = conversation_id;
    task_data->user_id = user_id;
    task_data->callback_ptr = new StreamCallback(callback);
    
    BaseType_t result = xTaskCreate(
        [](void* param) {
            auto* data = static_cast<AiAgent::StreamingTaskData*>(param);
            auto* files = static_cast<std::vector<AiAgent::FileInfo>*>(data->files_ptr);
            auto* callback = static_cast<AiAgent::StreamCallback*>(data->callback_ptr);
            
            data->agent->ProcessStreamingRequest(
                data->query, *files, data->conversation_id, 
                data->user_id, *callback);
            
            delete files;
            delete callback;
            delete data;
            vTaskDelete(NULL);
        },
        "ai_agent_task",
        8192,  // 8KB栈大小
        task_data,
        5,     // 优先级
        &processing_task_handle_
    );
    
    if (result != pdPASS) {
        ESP_LOGE(TAG, "Failed to create processing task");
        is_processing_ = false;
        if (callback) {
            callback("", false, "创建处理任务失败");
        }
        return false;
    }
    
    return true;
}

void AiAgent::StopStreaming() {
    should_stop_ = true;
    is_processing_ = false;
    
    if (processing_task_handle_ != NULL) {
        vTaskDelete(processing_task_handle_);
        processing_task_handle_ = NULL;
    }
    
    // ESP_LOGI(TAG, "AI streaming stopped");
}

void AiAgent::ProcessStreamingRequest(
    const std::string& query,
    const std::vector<FileInfo>& files,
    const std::string& conversation_id,
    const std::string& user_id,
    StreamCallback callback) {
    
    // ESP_LOGI(TAG, "Processing streaming request to Dify API");
    
    // 直接使用Board的CreateHttp方法
    auto http = Board::GetInstance().CreateHttp();
    
    if (!http) {
        ESP_LOGE(TAG, "Failed to create HTTP client");
        if (callback) {
            callback("", true, "网络连接失败");
        }
        is_processing_ = false;
        return;
    }
    
    // 构建请求JSON
    std::string request_json = BuildRequestJson(query, files, conversation_id, user_id);
    ESP_LOGI(TAG, "Request JSON: %s", request_json.c_str());
    
    // 设置请求头
    http->SetHeader("Authorization", "Bearer " DIFY_API_KEY);
    http->SetHeader("Content-Type", "application/json");
    http->SetHeader("Content-Length", std::to_string(request_json.length()));
    http->SetHeader("Accept", "text/event-stream");
    http->SetHeader("Cache-Control", "no-cache");
    http->SetHeader("Connection", "keep-alive");
    
    // 构建请求URL
    std::string url = DIFY_API_BASE_URL "/chat-messages";
    ESP_LOGI(TAG, "Connecting to URL: %s", url.c_str());
    
    // 打开POST连接
    ESP_LOGI(TAG, "Attempting to open HTTP connection...");
    if (!http->Open("POST", url)) {
        ESP_LOGE(TAG, "Failed to connect to Dify API: %s", url.c_str());
        if (callback) {
            callback("", true, "连接AI服务失败: " + url);
        }
        is_processing_ = false;
        return;
    }
    ESP_LOGI(TAG, "HTTP connection opened successfully");
    
    // 发送POST数据
    ESP_LOGI(TAG, "Sending request data, size: %d bytes", request_json.length());
    ESP_LOGI(TAG, "Request data content: %s", request_json.c_str());
    
    int write_result = http->Write(request_json.c_str(), request_json.length());
    ESP_LOGI(TAG, "Write result: %d", write_result);
    
    if (write_result <= 0) {
        ESP_LOGE(TAG, "Failed to send request data, result: %d", write_result);
        if (callback) {
            callback("", true, "发送请求失败");
        }
        http->Close();
        is_processing_ = false;
        return;
    }
    ESP_LOGI(TAG, "Request data sent successfully, bytes written: %d", write_result);
    
    // 检查响应状态
    int status_code = http->GetStatusCode();
    if (status_code != 200) {
        ESP_LOGE(TAG, "Dify API returned status code: %d", status_code);
        if (callback) {
            callback("", true, "AI服务返回错误: " + std::to_string(status_code));
        }
        http->Close();
        is_processing_ = false;
        return;
    }
    
    // ESP_LOGI(TAG, "Connected to Dify API, starting to read stream");
    
    // 流式读取SSE数据 - 减少缓冲区大小以节省栈空间
    char buffer[1024];  // 从2048减少到1024
    std::string accumulated_data;
    std::string current_conversation_id;
    
    // 添加超时机制和看门狗喂狗
    uint32_t start_time = esp_timer_get_time();
    uint32_t last_wdt_reset = start_time;
    const uint32_t TIMEOUT_MS = 60000; // 60秒超时
    const uint32_t WDT_RESET_INTERVAL_MS = 5000; // 每5秒喂一次狗
    
    while (!should_stop_ && is_processing_.load()) {
        // 检查超时
        uint32_t current_time = esp_timer_get_time();
        if (current_time - start_time > TIMEOUT_MS * 1000) {
            // ESP_LOGW(TAG, "Stream timeout after %" PRIu32 " ms", TIMEOUT_MS);
            if (callback) {
                callback("", true, "请求超时");
            }
            break;
        }
        
        // 定期喂狗
        if (current_time - last_wdt_reset > WDT_RESET_INTERVAL_MS * 1000) {
            esp_task_wdt_reset();
            last_wdt_reset = current_time;
        }
        int bytes_read = http->Read(buffer, sizeof(buffer) - 1);
        ESP_LOGI(TAG, "Read %d bytes from stream", bytes_read);
        
        if (bytes_read <= 0) {
            // 检查是否是正常结束
            if (bytes_read == 0) {
                ESP_LOGI(TAG, "Stream ended normally");
                break;
            } else {
                ESP_LOGE(TAG, "Failed to read from stream: %d", bytes_read);
                if (callback) {
                    callback("", true, "读取数据流失败");
                }
                break;
            }
        }
        
        buffer[bytes_read] = '\0';
        std::string chunk(buffer);
        ESP_LOGI(TAG, "Received chunk: %s", chunk.c_str());
        
        // 限制accumulated_data的大小，防止内存溢出
        if (accumulated_data.length() + chunk.length() > 10240) { // 限制为10KB
            // ESP_LOGW(TAG, "Accumulated data too large, truncating");
            accumulated_data = accumulated_data.substr(accumulated_data.length() / 2); // 保留后半部分
        }
        accumulated_data += chunk;
        
        // 解析SSE数据
        ParseSSEData(chunk, [&](const std::string& data, bool is_final, const std::string& error) {
            if (!error.empty()) {
                ESP_LOGE(TAG, "SSE parsing error: %s", error.c_str());
                if (callback) {
                    callback("", true, error);
                }
                return;
            }
            
            if (is_final) {
                // ESP_LOGI(TAG, "Stream completed");
                if (callback) {
                    callback("", true, "");
                }
                is_processing_ = false;
                return;
            }
            
            // 实时输出数据
            if (callback && !data.empty()) {
                ESP_LOGI(TAG, "About to call callback with data: %s", data.c_str());
                callback(data, false, "");
                ESP_LOGI(TAG, "Callback completed");
            }
        });
        
        // 如果解析过程中设置了final标志，退出循环
        if (!is_processing_.load()) {
            break;
        }
    }
    
    http->Close();
    is_processing_ = false;
    // ESP_LOGI(TAG, "AI streaming request completed");
}

std::string AiAgent::BuildRequestJson(
    const std::string& query,
    const std::vector<FileInfo>& files,
    const std::string& conversation_id,
    const std::string& user_id) {
    
    cJSON* json = cJSON_CreateObject();
    
    // inputs (空对象)
    cJSON* inputs = cJSON_CreateObject();
    cJSON_AddItemToObject(json, "inputs", inputs);
    
    // query
    cJSON_AddStringToObject(json, "query", query.c_str());
    
    // response_mode
    cJSON_AddStringToObject(json, "response_mode", "streaming");
    
    // conversation_id
    if (!conversation_id.empty()) {
        cJSON_AddStringToObject(json, "conversation_id", conversation_id.c_str());
    } else {
        cJSON_AddStringToObject(json, "conversation_id", "");
    }
    
    // user
    cJSON_AddStringToObject(json, "user", user_id.c_str());
    
    // files
    if (!files.empty()) {
        cJSON* files_array = cJSON_CreateArray();
        for (const auto& file : files) {
            cJSON* file_obj = cJSON_CreateObject();
            cJSON_AddStringToObject(file_obj, "type", file.type.c_str());
            cJSON_AddStringToObject(file_obj, "transfer_method", file.transfer_method.c_str());
            cJSON_AddStringToObject(file_obj, "url", file.url.c_str());
            if (!file.name.empty()) {
                cJSON_AddStringToObject(file_obj, "name", file.name.c_str());
            }
            cJSON_AddItemToArray(files_array, file_obj);
        }
        cJSON_AddItemToObject(json, "files", files_array);
    }
    
    char* json_string = cJSON_PrintUnformatted(json);
    std::string result(json_string);
    
    cJSON_free(json_string);
    cJSON_Delete(json);
    
    return result;
}

void AiAgent::ParseSSEData(const std::string& data, StreamCallback callback) {
    std::istringstream stream(data);
    std::string line;
    
    while (std::getline(stream, line)) {
        // 去除行尾的回车符
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        
        // 跳过空行
        if (line.empty()) {
            continue;
        }
        
        // 解析SSE格式: data: {content}
        if (line.substr(0, 5) == "data:") {
            std::string content = line.substr(5);
            
            // 去除前导空格
            content.erase(0, content.find_first_not_of(" \t"));
            ESP_LOGI(TAG, "Parsing SSE content: %s", content.c_str());
            
            // 检查是否是结束标记
            if (content == "[DONE]") {
                ESP_LOGI(TAG, "Received [DONE] marker");
                if (callback) {
                    callback("", true, "");
                }
                return;
            }
            
            // 尝试解析JSON数据
            cJSON* json = cJSON_Parse(content.c_str());
            if (json) {
                ESP_LOGI(TAG, "JSON parsed successfully");
                // 提取消息内容
                cJSON* answer = cJSON_GetObjectItem(json, "answer");
                cJSON* conversation_id = cJSON_GetObjectItem(json, "conversation_id");
                cJSON* error = cJSON_GetObjectItem(json, "error");
                
                if (cJSON_IsString(error) && strlen(error->valuestring) > 0) {
                    ESP_LOGE(TAG, "Dify API error: %s", error->valuestring);
                    if (callback) {
                        callback("", true, std::string(error->valuestring));
                    }
                    cJSON_Delete(json);
                    return;
                }
                
                if (cJSON_IsString(answer) && strlen(answer->valuestring) > 0) {
                    ESP_LOGI(TAG, "Found answer: %s", answer->valuestring);
                    // 更新对话ID
                    if (cJSON_IsString(conversation_id)) {
                        std::lock_guard<std::mutex> lock(conversation_mutex_);
                        current_conversation_id_ = std::string(conversation_id->valuestring);
                    }
                    
                    // 输出答案内容
                    if (callback) {
                        ESP_LOGI(TAG, "Calling callback with answer: %s", answer->valuestring);
                        callback(std::string(answer->valuestring), false, "");
                    }
                } else {
                    ESP_LOGW(TAG, "No valid answer found in JSON");
                }
                
                cJSON_Delete(json);
            } else {
                // 如果不是JSON，直接输出原始内容
                if (!content.empty() && callback) {
                    callback(content, false, "");
                }
            }
        }
    }
}

std::string AiAgent::UrlEncode(const std::string& str) {
    std::string encoded;
    char hex[4];
    
    for (size_t i = 0; i < str.length(); i++) {
        unsigned char c = str[i];
        
        if ((c >= 'A' && c <= 'Z') ||
            (c >= 'a' && c <= 'z') ||
            (c >= '0' && c <= '9') ||
            c == '-' || c == '_' || c == '.' || c == '~') {
            encoded += c;
        } else if (c == ' ') {
            encoded += '+';
        } else {
            snprintf(hex, sizeof(hex), "%%%02X", c);
            encoded += hex;
        }
    }
    return encoded;
}
