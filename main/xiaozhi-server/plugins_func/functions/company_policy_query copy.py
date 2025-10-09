"""
公司行政制度查询工具
使用FastGPT API实现流式查询公司行政制度，如报销、出差等制度
"""

import asyncio
import aiohttp
import json
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

# 流式工具函数描述
COMPANY_POLICY_QUERY_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "company_policy_query",
        "description": (
            "图迹科技公司介绍，以及行政制度查询工具，可以实时查询公司简介和各项行政制度和政策。"
            "支持查询报销制度、出差制度、请假制度、考勤制度等。"
            "使用流式输出，实时返回查询结果。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "policy_type": {
                    "type": "string",
                    "description": "制度类型，如：报销、出差、请假、考勤、福利、培训、晋升等",
                    "enum": ["报销", "出差", "请假", "考勤", "福利", "培训", "晋升", "其他"]
                },
                "query": {
                    "type": "string",
                    "description": "具体查询内容或问题，如：'出差报销标准'、'请假流程'、'考勤规定'等",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认60秒",
                }
            },
            "required": ["policy_type", "query"],
        },
    },
}


@register_function("company_policy_query", COMPANY_POLICY_QUERY_FUNCTION_DESC, ToolType.STREAM_OUTPUT)
async def company_policy_query(conn, policy_type: str, query: str, timeout: int = 60, stream_callback=None):
    """
    公司行政制度查询函数
    
    Args:
        conn: 连接对象
        policy_type: 制度类型
        query: 具体查询内容
        timeout: 超时时间
        stream_callback: 流式回调函数
    """
    try:
        # 从配置获取FastGPT API地址和密钥
        api_base_url = conn.config["plugins"]["company_policy_query"].get(
            "api_url", "https://cloud.fastgpt.cn/api"
        )
        api_key = conn.config["plugins"]["company_policy_query"].get(
            "api_key", "fastgpt-fiLsgV0lDKUGVdAK80XPXWWlEniQHo8tpbPklKDNqdbzGlMJxAWQxj"
        )
        
        # 构建完整的API地址
        api_url = f"{api_base_url}/v1/chat/completions"
        
        logger.bind(tag=TAG).info(f"开始查询公司制度: {policy_type} - {query}, API: {api_url}")
        
        # 构建请求数据
        request_data = {
            "chatId": f"policy_query_{int(asyncio.get_event_loop().time())}",
            "stream": True,
            "detail": False,
            "messages": [
                {
                    "role": "user", 
                    "content": f"请详细介绍公司的{policy_type}制度，包括相关流程、标准和要求。用户具体问题是：{query}"
                }
            ]
        }
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }
        
        # 使用aiohttp进行异步HTTP请求
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.post(
                api_url,
                headers=headers,
                json=request_data
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"FastGPT API请求失败，状态码: {response.status}, 响应: {error_text}"
                    logger.bind(tag=TAG).error(error_msg)
                    return ActionResponse(Action.ERROR, response=error_msg)
                
                # 流式读取数据
                chunk_count = 0
                content_chunk_count = 0  # 内容块计数器
                full_content = ""
                
                try:
                    async for line in response.content:
                        chunk_count += 1
                        if line:
                            try:
                                # 解码数据
                                line_str = line.decode('utf-8').strip()
                                logger.bind(tag=TAG).debug(f"数据块 {chunk_count}: {line_str}")
                                
                                if not line_str:
                                    continue
                                    
                                # 处理SSE格式数据
                                if line_str.startswith('data: '):
                                    data_str = line_str[6:]  # 移除 'data: ' 前缀
                                    
                                    # 检查是否是结束信号
                                    if data_str == '[DONE]':
                                        logger.bind(tag=TAG).info("接收到结束信号")
                                        break
                                        
                                    # 解析JSON数据
                                    try:
                                        data = json.loads(data_str)
                                        
                                        # 提取choices中的内容
                                        if "choices" in data and len(data["choices"]) > 0:
                                            choice = data["choices"][0]
                                            if "delta" in choice and "content" in choice["delta"]:
                                                content = choice["delta"]["content"]
                                                if content:
                                                    content_chunk_count += 1
                                                    full_content += content
                                                    
                                                    # 检查内容长度和特征，避免发送过长的内容块
                                                    if len(content) > 500 or (len(content) > 200 and '\n###' in content):  # 如果单个内容块过长或包含完整结构，跳过流式发送
                                                        has_structure = '\n###' in content
                                                        logger.bind(tag=TAG).warning(f"跳过过长的内容块，长度: {len(content)}, 包含完整结构: {has_structure}")
                                                        continue
                                                    
                                                    # 发送流式内容 - 使用message字段，与故事工具保持一致
                                                    if stream_callback:
                                                        await stream_callback({
                                                            "message": content,  # 使用message字段，与故事工具一致
                                                            "policy_type": policy_type,
                                                            "query": query,
                                                            "timestamp": int(asyncio.get_event_loop().time()),
                                                            "chunk_id": content_chunk_count
                                                        })
                                        
                                        # 检查是否是结束消息
                                        if data.get("choices") and len(data["choices"]) > 0:
                                            choice = data["choices"][0]
                                            if choice.get("finish_reason") == "stop":
                                                logger.bind(tag=TAG).info(f"流式传输完成，共处理 {chunk_count} 个数据块，{content_chunk_count} 个内容块")
                                                break
                                            
                                    except json.JSONDecodeError as e:
                                        logger.bind(tag=TAG).warning(f"JSON解析失败: {e}, 数据: {data_str}")
                                        # 如果不是JSON格式，直接发送文本
                                        if stream_callback and data_str:
                                            # 检查内容长度和特征，避免发送过长的内容块
                                            if len(data_str) > 500 or (len(data_str) > 200 and '\n###' in data_str):
                                                has_structure = '\n###' in data_str
                                                logger.bind(tag=TAG).warning(f"跳过过长的非JSON内容块，长度: {len(data_str)}, 包含完整结构: {has_structure}")
                                                continue
                                                
                                            content_chunk_count += 1
                                            await stream_callback({
                                                "message": data_str,  # 使用message字段，与故事工具一致
                                                "policy_type": policy_type,
                                                "query": query,
                                                "timestamp": int(asyncio.get_event_loop().time()),
                                                "chunk_id": content_chunk_count
                                            })
                                else:
                                    # 直接发送非SSE格式的数据
                                    if stream_callback and line_str:
                                        # 检查内容长度和特征，避免发送过长的内容块
                                        if len(line_str) > 500 or (len(line_str) > 200 and '\n###' in line_str):
                                            has_structure = '\n###' in line_str
                                            logger.bind(tag=TAG).warning(f"跳过过长的非SSE内容块，长度: {len(line_str)}, 包含完整结构: {has_structure}")
                                            continue
                                            
                                        content_chunk_count += 1
                                        await stream_callback({
                                            "message": line_str,  # 使用message字段，与故事工具一致
                                            "policy_type": policy_type,
                                            "query": query,
                                            "timestamp": int(asyncio.get_event_loop().time()),
                                            "chunk_id": content_chunk_count
                                        })
                                        
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"处理数据行时出错: {e}")
                                continue
                        else:
                            logger.bind(tag=TAG).debug(f"空数据块 {chunk_count}")
                        
                        # 防止无限循环
                        if chunk_count > 1000:
                            logger.bind(tag=TAG).warning("数据块过多，停止读取")
                            break
                            
                except Exception as e:
                    logger.bind(tag=TAG).error(f"流式读取失败: {e}")
                    
                    # 尝试非流式请求作为备选
                    try:
                        logger.bind(tag=TAG).info("尝试非流式请求作为备选")
                        non_stream_data = request_data.copy()
                        non_stream_data["stream"] = False
                        
                        async with session.post(
                            api_url,
                            headers=headers,
                            json=non_stream_data
                        ) as fallback_response:
                            
                            if fallback_response.status == 200:
                                fallback_result = await fallback_response.json()
                                logger.bind(tag=TAG).info("非流式请求成功")
                                
                                # 提取响应内容
                                if "choices" in fallback_result and len(fallback_result["choices"]) > 0:
                                    content = fallback_result["choices"][0].get("message", {}).get("content", "")
                                    if content:
                                        full_content = content  # 保存完整内容
                                        # 检查内容长度和特征，避免发送过长的内容块
                                        if len(content) > 500 or (len(content) > 200 and '\n###' in content):
                                            has_structure = '\n###' in content
                                            logger.bind(tag=TAG).warning(f"跳过过长的fallback内容块，长度: {len(content)}, 包含完整结构: {has_structure}")
                                        else:
                                            if stream_callback:
                                                await stream_callback({
                                                    "message": content,  # 使用message字段，与故事工具一致
                                                    "policy_type": policy_type,
                                                    "query": query,
                                                    "timestamp": int(asyncio.get_event_loop().time()),
                                                    "type": "fallback_response"
                                                })
                            else:
                                error_text = await fallback_response.text()
                                logger.bind(tag=TAG).error(f"非流式请求也失败: {fallback_response.status}, {error_text}")
                                
                    except Exception as e2:
                        logger.bind(tag=TAG).error(f"备选请求也失败: {e2}")
                
                # 返回成功结果，包含完整的查询内容
                final_result = full_content if full_content else f"关于{policy_type}制度的查询已完成。"
                logger.bind(tag=TAG).info(f"返回查询结果，内容长度: {len(final_result)} 字符")
                return ActionResponse(
                    Action.STREAM_RESPONSE, 
                    result=final_result
                )
                
    except asyncio.TimeoutError:
        error_msg = f"制度查询超时（{timeout}秒）"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
        
    except aiohttp.ClientError as e:
        error_msg = f"网络请求错误: {str(e)}"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
        
    except Exception as e:
        error_msg = f"制度查询执行错误: {str(e)}"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
