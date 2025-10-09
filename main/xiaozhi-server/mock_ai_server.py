#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟AI流式回复服务器
用于测试ESP32的AI Agent功能
"""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

# 配置参数
CONFIG = {
    'CHUNK_DELAY': 0.1,  # 每个chunk的间隔时间（秒）- 减少到0.1秒
    'HOST': '0.0.0.0',   # 服务器监听地址
    'PORT': 8080,        # 服务器端口
}

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockAIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """处理POST请求"""
        try:
            # 解析URL
            parsed_url = urlparse(self.path)
            
            # 检查是否是聊天接口
            if parsed_url.path == '/v1/chat-messages':
                self.handle_chat_request()
            else:
                self.send_error(404, "Not Found")
                
        except Exception as e:
            logger.error(f"处理请求时出错: {e}")
            self.send_error(500, "Internal Server Error")
    
    def handle_chat_request(self):
        """处理聊天请求"""
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            logger.info(f"收到请求，Content-Length: {content_length}")
            
            if content_length == 0:
                logger.error("请求体为空")
                self.send_error(400, "Bad Request - Empty body")
                return
                
            post_data = self.rfile.read(content_length)
            logger.info(f"读取到数据: {len(post_data)} 字节")
            
            # 打印原始数据用于调试
            try:
                raw_text = post_data.decode('utf-8')
                logger.info(f"原始请求数据: '{raw_text}'")
            except UnicodeDecodeError:
                logger.error(f"无法解码为UTF-8，原始字节: {post_data}")
                self.send_error(400, "Bad Request - Invalid encoding")
                return
            
            # 检查是否为空
            if not raw_text.strip():
                logger.error("请求体为空字符串")
                self.send_error(400, "Bad Request - Empty body")
                return
            
            # 处理可能的HTTP分块传输编码或数据前缀
            json_text = raw_text
            
            # 首先尝试找到JSON的开始位置
            json_start = raw_text.find('{')
            if json_start != -1:
                # 找到JSON开始位置，提取从该位置开始的数据
                json_text = raw_text[json_start:]
                logger.info(f"从位置{json_start}提取JSON: '{json_text}'")
                
                # 如果数据被截断，尝试修复JSON
                if not json_text.endswith('}'):
                    # 数据可能被截断，尝试修复JSON
                    if json_text.endswith('"esp32-us'):
                        # 修复被截断的user字段
                        json_text = json_text.replace('"esp32-us', '"esp32-user"}')
                        logger.info(f"修复截断的user字段: '{json_text}'")
                    else:
                        # 尝试找到最后一个完整的JSON
                        json_end = json_text.rfind('}')
                        if json_end != -1:
                            json_text = json_text[:json_end+1]
                            logger.info(f"截断后提取完整JSON: '{json_text}'")
                        else:
                            logger.warning(f"JSON数据可能不完整: '{json_text}'")
            else:
                logger.error(f"未找到JSON开始标记: '{raw_text}'")
            
            # 解析JSON
            try:
                request_data = json.loads(json_text)
                logger.info(f"JSON解析成功: {request_data}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.error(f"尝试解析的数据: '{json_text}'")
                logger.error(f"原始数据: '{raw_text}'")
                self.send_error(400, "Bad Request - Invalid JSON")
                return
            
            # 支持不同的JSON格式
            query = request_data.get('query', '')
            conversation_id = request_data.get('conversation_id', '')
            user_id = request_data.get('user', 'esp32-user')
            
            # 如果没有找到query，尝试其他可能的字段名
            if not query:
                query = request_data.get('message', '')
                query = request_data.get('text', '')
            
            logger.info(f"解析结果 - query: '{query}', conversation_id: '{conversation_id}', user: '{user_id}'")
            
            logger.info(f"收到请求 - 用户: {user_id}, 查询: {query[:50]}...")
            
            # 设置SSE响应头
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', 'Cache-Control')
            self.end_headers()
            
            # 生成模拟的流式回复
            self.send_streaming_response(query, conversation_id, user_id)
            
        except Exception as e:
            logger.error(f"处理聊天请求时出错: {e}", exc_info=True)
            self.send_error(500, "Internal Server Error")
    
    def send_streaming_response(self, query, conversation_id, user_id):
        """发送流式回复"""
        try:
            # 根据查询内容生成不同的回复
            response_chunks = self.generate_mock_response(query)
            
            for i, chunk in enumerate(response_chunks):
                # 检查连接是否还活着
                if not self.connection:
                    break
                
                # 构造SSE数据
                event_data = {
                    "event": "message",
                    "task_id": f"mock-task-{int(time.time())}",
                    "id": f"msg-{i}",
                    "message_id": f"msg-{i}",
                    "conversation_id": conversation_id or f"conv-{int(time.time())}",
                    "mode": "chat",
                    "answer": chunk,
                    "metadata": {
                        "usage": {
                            "prompt_tokens": 10,
                            "prompt_unit_price": "0.0",
                            "prompt_price_unit": "0.0",
                            "prompt_price": "0.0",
                            "completion_tokens": len(chunk),
                            "completion_unit_price": "0.0",
                            "completion_price_unit": "0.0",
                            "completion_price": "0.0",
                            "total_tokens": 10 + len(chunk),
                            "total_price": "0.0",
                            "currency": "USD",
                            "latency": 0.1
                        },
                        "retriever_resources": []
                    },
                    "created_at": int(time.time())
                }
                
                # 发送SSE数据
                sse_data = f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                logger.info(f"发送SSE数据: {sse_data}")
                self.wfile.write(sse_data.encode('utf-8'))
                self.wfile.flush()
                
                # 模拟网络延迟 - 使用配置的间隔时间
                time.sleep(CONFIG['CHUNK_DELAY'])
            
            # 发送结束事件
            end_event = {
                "event": "message_end",
                "task_id": f"mock-task-{int(time.time())}",
                "id": f"msg-end",
                "message_id": f"msg-end",
                "conversation_id": conversation_id or f"conv-{int(time.time())}",
                "mode": "chat",
                "answer": "",
                "metadata": {
                    "usage": {
                        "prompt_tokens": 10,
                        "prompt_unit_price": "0.0",
                        "prompt_price_unit": "0.0",
                        "prompt_price": "0.0",
                        "completion_tokens": sum(len(chunk) for chunk in response_chunks),
                        "completion_unit_price": "0.0",
                        "completion_price_unit": "0.0",
                        "completion_price": "0.0",
                        "total_tokens": 10 + sum(len(chunk) for chunk in response_chunks),
                        "total_price": "0.0",
                        "currency": "USD",
                        "latency": 0.1
                    },
                    "retriever_resources": []
                },
                "created_at": int(time.time())
            }
            
            sse_data = f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n"
            logger.info(f"发送结束事件: {sse_data}")
            self.wfile.write(sse_data.encode('utf-8'))
            self.wfile.flush()
            
            logger.info("流式回复发送完成")
            
        except Exception as e:
            logger.error(f"发送流式回复时出错: {e}")
    
    def generate_mock_response(self, query):
        """根据查询生成模拟回复"""
        query_lower = query.lower()
        
        # 根据关键词生成不同的回复
        if "电价" in query or "electricity" in query_lower:
            return [
                "根据广东地区的最新数据，",
                "日前节点预测电价如下：\n\n",
                "**今日电价预测：**\n",
                "• 峰时电价：0.85元/kWh\n",
                "• 平时电价：0.55元/kWh\n",
                "• 谷时电价：0.25元/kWh\n\n",
                "**明日预测：**\n",
                "• 峰时电价：0.88元/kWh\n",
                "• 平时电价：0.58元/kWh\n",
                "• 谷时电价：0.28元/kWh\n\n",
                "建议在谷时进行大功率用电，可以节省电费。"
            ]
        elif "天气" in query or "weather" in query_lower:
            return [
                "根据气象部门的最新预报，",
                "广东地区未来几天的天气情况如下：\n\n",
                "**今日天气：**\n",
                "• 温度：22-28°C\n",
                "• 天气：多云转晴\n",
                "• 湿度：65%\n",
                "• 风力：2-3级\n\n",
                "**明日预报：**\n",
                "• 温度：20-26°C\n",
                "• 天气：晴转多云\n",
                "• 湿度：60%\n",
                "• 风力：1-2级\n\n",
                "天气总体良好，适合户外活动。"
            ]
        elif "你好" in query or "hello" in query_lower:
            return [
                "你好！我是小智AI助手，",
                "很高兴为您服务！\n\n",
                "我可以帮您：\n",
                "• 查询电价信息\n",
                "• 提供天气预报\n",
                "• 回答各种问题\n",
                "• 进行智能对话\n\n",
                "请告诉我您需要什么帮助？"
            ]
        else:
            return [
                "我收到了您的查询：",
                f"「{query}」\n\n",
                "这是一个模拟的AI回复。",
                "在实际应用中，这里会调用真实的AI模型。\n\n",
                "当前时间：",
                time.strftime("%Y-%m-%d %H:%M:%S"),
                "\n\n",
                "如果您需要测试特定功能，请尝试询问：\n",
                "• 电价查询\n",
                "• 天气信息\n",
                "• 其他问题"
            ]
    
    def log_message(self, format, *args):
        """重写日志方法，减少输出"""
        pass

def start_mock_server(host=None, port=None):
    """启动模拟服务器"""
    # 使用配置参数或传入的参数
    host = host or CONFIG['HOST']
    port = port or CONFIG['PORT']
    
    server_address = (host, port)
    httpd = HTTPServer(server_address, MockAIHandler)
    
    logger.info(f"模拟AI服务器启动在 http://{host}:{port}")
    logger.info("支持的接口：")
    logger.info("  POST /v1/chat-messages - 聊天接口")
    logger.info(f"配置参数：")
    logger.info(f"  - 回复间隔: {CONFIG['CHUNK_DELAY']}秒")
    logger.info(f"  - 监听地址: {CONFIG['HOST']}:{CONFIG['PORT']}")
    logger.info("按 Ctrl+C 停止服务器")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务器停止")
        httpd.shutdown()

if __name__ == '__main__':
    start_mock_server()
