"""
电力交易数据查询工具
支持电力交易数据查询，市场交易规则查询等
包括：日前预测电价、实时预测电价、气象数据、电源出力、统调负荷等
"""

import asyncio
import aiohttp
import json
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

# 流式工具函数描述
POWER_DATA_QUERY_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "power_data_query",
        "description": (
            "电力交易数据查询工具，支持查询电力市场相关数据和交易规则。"
            "包括：日前预测电价、实时预测电价、气象数据（温度、风速、湿度等）、"
            "A类电源出力、B类电源出力、统调负荷等电力交易相关数据。"
            "使用流式输出，实时返回查询结果。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "data_type": {
                    "type": "string",
                    "description": "数据类型，如：日前预测电价、实时预测电价、气象数据、A类电源出力、B类电源出力、统调负荷、市场规则等",
                    "enum": [
                        "日前预测电价", "实时预测电价", "气象数据", "A类电源出力", 
                        "B类电源出力", "统调负荷", "市场规则", "交易数据", "其他"
                    ]
                },
                "query": {
                    "type": "string",
                    "description": "具体查询内容或问题，如：'明天的日前预测电价'、'今日实时电价'、'当前温度'、'A类电源出力情况'等",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认60秒",
                }
            },
            "required": ["data_type", "query"],
        },
    },
}


@register_function("power_data_query", POWER_DATA_QUERY_FUNCTION_DESC, ToolType.STREAM_OUTPUT)
async def power_data_query(conn, data_type: str, query: str, timeout: int = 60, stream_callback=None):
    """
    电力交易数据查询函数
    
    Args:
        conn: 连接对象
        data_type: 数据类型
        query: 具体查询内容
        timeout: 超时时间
        stream_callback: 流式回调函数
    """
    try:
        # 从配置获取API地址，如果没有配置则使用默认地址
        api_base_url = conn.config["plugins"]["power_data_query"].get(
            "api_url", "http://1.95.88.210:8888"
        )
        
        # 构建完整的API地址
        api_url = f"{api_base_url}/v1/chat/mcp"
        
        logger.bind(tag=TAG).info(f"开始查询电力数据: {data_type} - {query}, API: {api_url}")
        
        
        # 构建请求参数
        params = {
            "qa": query
        }
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }
        
        # 使用aiohttp进行异步HTTP请求
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(
                api_url,
                headers=headers,
                params=params
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    error_msg = f"电力数据API请求失败，状态码: {response.status}, 响应: {error_text}"
                    logger.bind(tag=TAG).error(error_msg)
                    return ActionResponse(Action.ERROR, response=error_msg)
                
                
                # 流式读取数据 - 优化版本，减少卡顿
                chunk_count = 0
                content_chunk_count = 0  # 内容块计数器
                full_content = ""
                content_buffer = ""  # 内容缓冲区，用于合并小片段
                last_send_time = 0  # 上次发送时间
                min_send_interval = 0.5  # 最小发送间隔（秒）
                min_content_length = 10  # 最小内容长度
                
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
                                        # 发送缓冲区中剩余的内容
                                        if content_buffer and stream_callback:
                                            await stream_callback({
                                                "message": content_buffer,
                                                "data_type": data_type,
                                                "query": query,
                                                "timestamp": int(asyncio.get_event_loop().time()),
                                                "chunk_id": content_chunk_count + 1,
                                                "is_final": True
                                            })
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
                                                    content_buffer += content
                                                    
                                                    # 检查是否应该发送缓冲区内容
                                                    current_time = asyncio.get_event_loop().time()
                                                    should_send = (
                                                        len(content_buffer) >= min_content_length and
                                                        (current_time - last_send_time) >= min_send_interval
                                                    ) or len(content_buffer) > 100  # 或者缓冲区过长
                                                    
                                                    if should_send and stream_callback:
                                                        # 检查内容长度和特征，避免发送过长的内容块
                                                        if len(content_buffer) > 500 or (len(content_buffer) > 200 and '\n###' in content_buffer):
                                                            has_structure = '\n###' in content_buffer
                                                            logger.bind(tag=TAG).warning(f"跳过过长的内容块，长度: {len(content_buffer)}, 包含完整结构: {has_structure}")
                                                            content_buffer = ""  # 清空缓冲区
                                                            continue
                                                        
                                                        await stream_callback({
                                                            "message": content_buffer,
                                                            "data_type": data_type,
                                                            "query": query,
                                                            "timestamp": int(current_time),
                                                            "chunk_id": content_chunk_count
                                                        })
                                                        content_buffer = ""  # 清空缓冲区
                                                        last_send_time = current_time
                                        
                                        # 检查是否是结束消息
                                        if data.get("choices") and len(data["choices"]) > 0:
                                            choice = data["choices"][0]
                                            if choice.get("finish_reason") == "stop":
                                                # 发送缓冲区中剩余的内容
                                                if content_buffer and stream_callback:
                                                    await stream_callback({
                                                        "message": content_buffer,
                                                        "data_type": data_type,
                                                        "query": query,
                                                        "timestamp": int(asyncio.get_event_loop().time()),
                                                        "chunk_id": content_chunk_count + 1,
                                                        "is_final": True
                                                    })
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
                                                "message": data_str,
                                                "data_type": data_type,
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
                                            "message": line_str,
                                            "data_type": data_type,
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
                        
                        # 修改请求头为非流式
                        fallback_headers = headers.copy()
                        fallback_headers["Accept"] = "application/json"
                        
                        async with session.get(
                            api_url,
                            headers=fallback_headers,
                            params=params
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
                                                    "message": content,  # 使用message字段，与其他工具一致
                                                    "data_type": data_type,
                                                    "query": query,
                                                    "timestamp": int(asyncio.get_event_loop().time()),
                                                    "type": "fallback_response"
                                                })
                            else:
                                error_text = await fallback_response.text()
                                logger.bind(tag=TAG).error(f"非流式请求也失败: {fallback_response.status}, {error_text}")
                                
                    except Exception as e2:
                        logger.bind(tag=TAG).error(f"备选请求也失败: {e2}")
                
                # 返回成功结果，不包含完整内容，避免重复播放
                logger.bind(tag=TAG).info(f"流式查询完成，共处理 {content_chunk_count} 个内容块")
                return ActionResponse(
                    Action.STREAM_RESPONSE, 
                    result=f"。{query}查询任务已执行完成。"
                )
                
    except asyncio.TimeoutError:
        error_msg = f"电力数据查询超时（{timeout}秒）"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
        
    except aiohttp.ClientError as e:
        error_msg = f"网络请求错误: {str(e)}"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
        
    except Exception as e:
        error_msg = f"电力数据查询执行错误: {str(e)}"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
