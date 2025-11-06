"""
流式数据查询工具示例
使用新的STREAM_OUTPUT工具类型实现流式数据输出
"""

import asyncio
import aiohttp
import json
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

# 流式工具函数描述
STREAM_DATA_QUERY_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "stream_data_query",
        "description": (
            "流式数据查询工具，可以实时获取和推送数据流。"
            "支持查询名字的生辰八字。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "查询内容或请求参数",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认60秒",
                }
            },
            "required": ["query"],
        },
    },
}


@register_function("stream_data_query", STREAM_DATA_QUERY_FUNCTION_DESC, ToolType.STREAM_OUTPUT)
async def stream_data_query(conn, query: str, timeout: int = 60, stream_callback=None):
    """
    流式数据查询函数
    
    Args:
        conn: 连接对象
        query: 查询内容
        timeout: 超时时间
        stream_callback: 流式回调函数
    """
    try:
        # 从配置获取API地址和密钥
        api_base_url = conn.config["plugins"]["stream_data_query"].get(
            "api_url", "http://localhost:8008"
        )
        api_key = conn.config["plugins"]["stream_data_query"].get(
            "api_key", "123456789"
        )
        
        # 构建完整的API地址，密钥作为GET参数
        api_url = f"{api_base_url}/api/message?key={api_key}"
        
        logger.bind(tag=TAG).info(f"开始流式查询: {query}, API: {api_url}")
        
        # 构建请求数据
        request_data = {
            "message": query,
            "timestamp": int(asyncio.get_event_loop().time())
        }
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }
        
        # 构建GET请求URL，将消息作为参数
        get_url = f"{api_url}&message={request_data['message']}"
        
        # 使用aiohttp进行异步HTTP请求
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(
                get_url,
                headers=headers
            ) as response:
                
                if response.status != 200:
                    error_msg = f"API请求失败，状态码: {response.status}"
                    logger.bind(tag=TAG).error(error_msg)
                    return ActionResponse(Action.ERROR, response=error_msg)
                
                # 流式读取数据
                chunk_count = 0
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
                                        
                                        # 检查是否是结束消息
                                        if data.get("message") == "DONE":
                                            total_messages = data.get("total_messages", chunk_count)
                                            logger.bind(tag=TAG).info(f"流式传输完成，共处理 {total_messages} 个消息")
                                            break
                                        
                                        # 提取message字段并发送
                                        message_content = data.get("message", "")
                                        if message_content and stream_callback:
                                            await stream_callback({
                                                "message": message_content,
                                                "timestamp": data.get("timestamp"),
                                                "elapsed_time": data.get("elapsed_time")
                                            })
                                            
                                    except json.JSONDecodeError:
                                        # 如果不是JSON格式，直接发送文本
                                        if stream_callback:
                                            await stream_callback({"text": data_str})
                                else:
                                    # 直接发送非SSE格式的数据
                                    if stream_callback:
                                        await stream_callback({"text": line_str})
                                        
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"处理数据行时出错: {e}")
                                continue
                        else:
                            logger.bind(tag=TAG).debug(f"空数据块 {chunk_count}")
                        
                        # 防止无限循环
                        if chunk_count > 100:
                            logger.bind(tag=TAG).warning("数据块过多，停止读取")
                            break
                            
                except Exception as e:
                    logger.bind(tag=TAG).error(f"流式读取失败: {e}")
                    
                    # 尝试读取完整响应作为备选
                    try:
                        full_content = await response.text()
                        logger.bind(tag=TAG).info(f"备选完整响应: {full_content}")
                        
                        if stream_callback:
                            await stream_callback({
                                "type": "fallback_response",
                                "data": full_content,
                                "error": str(e)
                            })
                    except Exception as e2:
                        logger.bind(tag=TAG).error(f"备选读取也失败: {e2}")
                
                # 返回成功结果
                return ActionResponse(
                    Action.STREAM_RESPONSE, 
                    result=f"数据已经查询完成播报完毕。"
                )
                
    except asyncio.TimeoutError:
        error_msg = f"数据查询超时（{timeout}秒）"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
        
    except aiohttp.ClientError as e:
        error_msg = f"网络请求错误: {str(e)}"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
        
    except Exception as e:
        error_msg = f"数据查询执行错误: {str(e)}"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)

