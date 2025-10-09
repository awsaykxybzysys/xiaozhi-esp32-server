"""
流式故事播放工具
演示如何使用新的STREAM_OUTPUT工具类型实现流式故事播放
"""

import asyncio
import aiohttp
import json
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

# 流式故事播放工具函数描述
STREAM_STORY_PLAYER_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "stream_story_player",
        "description": (
            "流式故事播放工具，可以实时播放故事内容。"
            "支持播放各种类型的故事，包括童话、寓言、小说等。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "story_type": {
                    "type": "string",
                    "description": "故事类型，如：童话、寓言、小说、神话等",
                },
                "story_theme": {
                    "type": "string", 
                    "description": "故事主题，如：冒险、爱情、友谊、成长等",
                },
                "story_length": {
                    "type": "string",
                    "description": "故事长度，如：短篇、中篇、长篇",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认120秒",
                }
            },
            "required": ["story_type"],
        },
    },
}


@register_function("stream_story_player", STREAM_STORY_PLAYER_FUNCTION_DESC, ToolType.STREAM_OUTPUT)
async def stream_story_player(conn, story_type: str, story_theme: str = "冒险", story_length: str = "短篇", timeout: int = 120, stream_callback=None):
    """
    流式故事播放函数
    
    Args:
        conn: 连接对象
        story_type: 故事类型
        story_theme: 故事主题
        story_length: 故事长度
        timeout: 超时时间
        stream_callback: 流式回调函数
    """
    try:
        # 从配置获取API地址和密钥
        api_base_url = conn.config["plugins"]["stream_story_player"].get(
            "api_url", "http://localhost:8008"
        )
        api_key = conn.config["plugins"]["stream_story_player"].get(
            "api_key", "123456789"
        )
        
        # 构建完整的API地址，密钥作为GET参数
        api_url = f"{api_base_url}/api/story?key={api_key}"
        
        # 构建故事请求内容
        story_request = f"请播放一个{story_length}的{story_type}故事，主题是{story_theme}"
        
        logger.bind(tag=TAG).info(f"开始播放故事: {story_request}, API: {api_url}")
        
        # 构建请求数据
        request_data = {
            "story_type": story_type,
            "story_theme": story_theme,
            "story_length": story_length,
            "request": story_request,
            "timestamp": int(asyncio.get_event_loop().time())
        }
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }
        
        # 构建GET请求URL，将故事请求作为参数
        get_url = f"{api_url}&story_type={story_type}&theme={story_theme}&length={story_length}&request={story_request}"
        
        # 使用aiohttp进行异步HTTP请求
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(
                get_url,
                headers=headers
            ) as response:
                
                if response.status != 200:
                    error_msg = f"故事API请求失败，状态码: {response.status}"
                    logger.bind(tag=TAG).error(error_msg)
                    return ActionResponse(Action.ERROR, response=error_msg)
                
                # 流式读取故事数据
                chunk_count = 0
                story_content = ""
                
                try:
                    async for line in response.content:
                        chunk_count += 1
                        if line:
                            try:
                                # 解码数据
                                line_str = line.decode('utf-8').strip()
                                logger.bind(tag=TAG).debug(f"故事数据块 {chunk_count}: {line_str}")
                                
                                if not line_str:
                                    continue
                                    
                                # 处理SSE格式数据
                                if line_str.startswith('data: '):
                                    data_str = line_str[6:]  # 移除 'data: ' 前缀
                                    
                                    # 检查是否是结束信号
                                    if data_str == '[DONE]':
                                        logger.bind(tag=TAG).info("故事播放结束")
                                        break
                                        
                                    # 解析JSON数据
                                    try:
                                        data = json.loads(data_str)
                                        
                                        # 检查是否是故事结束消息
                                        if data.get("type") == "story_end":
                                            total_chunks = data.get("total_chunks", chunk_count)
                                            logger.bind(tag=TAG).info(f"故事播放完成，共处理 {total_chunks} 个片段")
                                            break
                                        
                                        # 提取故事内容并发送
                                        if data.get("type") == "story_chunk":
                                            story_fragment = data.get("content", "")
                                            if story_fragment and stream_callback:
                                                # 累积故事内容
                                                story_content += story_fragment
                                                
                                                await stream_callback({
                                                    "message": story_fragment,
                                                    "story_type": story_type,
                                                    "story_theme": story_theme,
                                                    "fragment_number": data.get("chunk_number", chunk_count),
                                                    "total_chunks": data.get("total_chunks", 0),
                                                    "timestamp": data.get("timestamp")
                                                })
                                            
                                    except json.JSONDecodeError:
                                        # 如果不是JSON格式，直接发送文本
                                        if stream_callback:
                                            story_content += data_str
                                            await stream_callback({
                                                "message": data_str,
                                                "story_type": story_type,
                                                "fragment_number": chunk_count
                                            })
                                else:
                                    # 直接发送非SSE格式的数据
                                    if stream_callback:
                                        story_content += line_str
                                        await stream_callback({
                                            "message": line_str,
                                            "story_type": story_type,
                                            "fragment_number": chunk_count
                                        })
                                        
                            except Exception as e:
                                logger.bind(tag=TAG).error(f"处理故事数据行时出错: {e}")
                                continue
                        else:
                            logger.bind(tag=TAG).debug(f"空故事数据块 {chunk_count}")
                        
                        # 防止无限循环
                        if chunk_count > 200:  # 故事可能比较长，增加限制
                            logger.bind(tag=TAG).warning("故事数据块过多，停止读取")
                            break
                            
                except Exception as e:
                    logger.bind(tag=TAG).error(f"流式故事读取失败: {e}")
                    
                    # 尝试读取完整响应作为备选
                    try:
                        full_content = await response.text()
                        logger.bind(tag=TAG).info(f"备选完整故事响应: {full_content}")
                        
                        if stream_callback:
                            await stream_callback({
                                "type": "fallback_response",
                                "data": full_content,
                                "error": str(e)
                            })
                    except Exception as e2:
                        logger.bind(tag=TAG).error(f"备选故事读取也失败: {e2}")
                
                # 返回成功结果
                return ActionResponse(
                    Action.STREAM_RESPONSE, 
                    result=f"故事播放完成，共处理 {chunk_count} 个片段，故事类型：{story_type}，主题：{story_theme}"
                )
                
    except asyncio.TimeoutError:
        error_msg = f"故事播放超时（{timeout}秒）"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
        
    except aiohttp.ClientError as e:
        error_msg = f"故事网络请求错误: {str(e)}"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
        
    except Exception as e:
        error_msg = f"故事播放执行错误: {str(e)}"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, response=error_msg)
