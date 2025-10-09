"""服务端插件工具执行器"""

import json
from typing import Dict, Any
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import all_function_registry, Action, ActionResponse


class ServerPluginExecutor(ToolExecutor):
    """服务端插件工具执行器"""

    def __init__(self, conn):
        self.conn = conn
        self.config = conn.config
        from config.logger import setup_logging
        self.logger = setup_logging()

    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """执行服务端插件工具"""
        func_item = all_function_registry.get(tool_name)
        if not func_item:
            return ActionResponse(
                action=Action.NOTFOUND, response=f"插件函数 {tool_name} 不存在"
            )

        try:
            # 根据工具类型决定如何调用
            if hasattr(func_item, "type"):
                func_type = func_item.type
                if func_type.code in [4, 5]:  # SYSTEM_CTL, IOT_CTL (需要conn参数)
                    result = func_item.func(conn, **arguments)
                elif func_type.code == 2:  # WAIT
                    result = func_item.func(**arguments)
                elif func_type.code == 3:  # CHANGE_SYS_PROMPT
                    result = func_item.func(conn, **arguments)
                elif func_type.code == 18:  # STREAM_OUTPUT (流式输出)
                    # 流式工具需要特殊处理，创建流式回调函数
                    stream_callback = self._create_stream_callback(conn, tool_name)
                    result = await func_item.func(conn, stream_callback=stream_callback, **arguments)
                else:
                    result = func_item.func(**arguments)
            else:
                # 默认不传conn参数
                result = func_item.func(**arguments)

            return result

        except Exception as e:
            return ActionResponse(
                action=Action.ERROR,
                response=str(e),
            )

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """获取所有注册的服务端插件工具"""
        tools = {}

        # 获取必要的函数
        necessary_functions = ["handle_exit_intent", "get_lunar"]

        # 获取配置中的函数
        config_functions = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ].get("functions", [])

        # 转换为列表
        if not isinstance(config_functions, list):
            try:
                config_functions = list(config_functions)
            except TypeError:
                config_functions = []

        # 合并所有需要的函数
        all_required_functions = list(set(necessary_functions + config_functions))

        for func_name in all_required_functions:
            func_item = all_function_registry.get(func_name)
            if func_item:
                tools[func_name] = ToolDefinition(
                    name=func_name,
                    description=func_item.description,
                    tool_type=ToolType.SERVER_PLUGIN,
                )

        return tools

    def has_tool(self, tool_name: str) -> bool:
        """检查是否有指定的服务端插件工具"""
        return tool_name in all_function_registry

    def _create_stream_callback(self, conn, tool_name: str):
        """创建流式回调函数"""
        async def stream_callback(data_chunk):
            """
            流式数据回调函数
            按照指定格式处理数据片段: {'content':[{'type':'text','data':'内容'}],'isError':False}
            """
            self.logger.info(f"stream_callback被调用，数据: {data_chunk}")
            try:
                # 构建标准格式的响应数据
                # 如果data_chunk包含message字段，优先使用message内容
                if isinstance(data_chunk, dict) and 'message' in data_chunk:
                    content_data = data_chunk['message']
                else:
                    content_data = json.dumps(data_chunk, ensure_ascii=False)
                
                response_data = {
                    'content': [{
                        'type': 'text',
                        'data': content_data
                    }],
                    'isError': False
                }
                
                # 通过连接发送流式数据
                # if hasattr(conn, 'send_stream_data'):
                #     await conn.send_stream_data(response_data)
                # elif hasattr(conn, 'websocket') and hasattr(conn.websocket, 'send'):
                #     # 使用websocket发送流式数据
                #     await conn.websocket.send(json.dumps(response_data, ensure_ascii=False))
                # elif hasattr(conn, 'send'):
                #     await conn.send(json.dumps(response_data, ensure_ascii=False))
                # else:
                #     self.logger.warning("连接对象没有可用的发送方法")
                
                # 从源头解决问题：在company_policy_query.py中过滤完整响应，这里不再需要重复检测
                
                # 立即播放当前数据片段的语音
                if hasattr(conn, 'tts') and hasattr(conn.tts, 'tts_one_sentence'):
                    from core.providers.tts.dto.dto import ContentType
                    conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=content_data)
                elif hasattr(conn, 'tts') and hasattr(conn.tts, 'tts_text_queue'):
                    # 使用队列方式播放
                    self.logger.info(f"通过队列播放流式数据语音: {content_data}")
                    conn.tts.tts_text_queue.put(content_data)
                else:
                    self.logger.warning("连接对象没有可用的TTS播放方法")
                # 只发送数据，不直接播放TTS，让系统自动处理
                # 避免在stream_callback中直接调用TTS，防止重复播放
                self.logger.info(f"流式数据已发送，内容长度: {len(content_data)}")
                        
            except Exception as e:
                self.logger.error(f"stream_callback执行出错: {e}")
                # 发送错误信息
                error_data = {
                    'content': [{
                        'type': 'text', 
                        'data': json.dumps({'error': str(e)}, ensure_ascii=False)
                    }],
                    'isError': True
                }
                if hasattr(conn, 'send_stream_data'):
                    await conn.send_stream_data(error_data)
                    
        return stream_callback
