"""
WebSocket处理器
处理工具端和客户端的WebSocket连接
"""

import json
from ..core.connection_manager import connection_manager
from ..utils.logger import get_logger
from ..utils.jsonrpc import (
    create_tool_not_connected_error,
    create_forward_failed_error,
)
from .sse_handler import sse_handler

logger = get_logger()


class WebSocketHandler:
    """WebSocket处理器"""

    def __init__(self):
        pass

    async def _handle_tool_message(self, agent_id: str, message: str):
        """处理工具端消息"""
        try:
            # 解析消息
            logger.debug(f"收到工具端消息: {agent_id} - {message}")

            # 尝试解析JSON-RPC响应消息
            try:
                message_data = json.loads(message)
                # 还原JSON-RPC ID并获取目标连接UUID
                connection_uuid, restored_message = (
                    connection_manager.restore_jsonrpc_message(message_data)
                )

                if connection_uuid:
                    # 有特定的目标连接，发送给该连接
                    success = await connection_manager.forward_to_robot_by_uuid(
                        connection_uuid, restored_message
                    )
                    if not success:
                        logger.error(f"转发消息给特定客户端连接失败: {connection_uuid}")
                else:
                    # 没有特定目标，尝试转发给SSE工具
                    sse_success = await sse_handler.send_mcp_response_to_sse(
                        agent_id, message_data
                    )
                    if not sse_success:
                        logger.error(f"没有特定目标，无法转发消息")
            except json.JSONDecodeError:
                # 如果不是JSON格式，按原来的方式处理
                logger.error(f"由于消息不是JSON格式，已忽略: {message}")

        except json.JSONDecodeError:
            logger.error(f"工具端消息格式错误: {message}")
        except Exception as e:
            logger.error(f"处理工具端消息时发生错误: {e}")

    async def _handle_robot_message(
        self, agent_id: str, message: str, connection_uuid: str
    ):
        """处理客户端消息"""
        try:
            # 解析消息
            logger.debug(
                f"收到客户端消息: {agent_id} (UUID: {connection_uuid}) - {message}"
            )

            # 尝试解析JSON-RPC消息以获取id
            request_id = None
            transformed_message = message
            try:
                message_data = json.loads(message)
                request_id = message_data.get("id")

                # 转换JSON-RPC ID
                transformed_message_data = connection_manager.transform_jsonrpc_message(
                    message_data, connection_uuid
                )
                transformed_message = json.dumps(
                    transformed_message_data, ensure_ascii=False
                )

                logger.debug(
                    f"转换后的消息ID: {message_data.get('id')} -> {transformed_message_data.get('id')}"
                )

            except json.JSONDecodeError:
                logger.warning(f"客户端消息不是有效的JSON格式: {message}")
                # 如果消息不是JSON格式，仍然检查工具端连接状态

            # 检查是否有对应的工具端连接
            tool_connected = connection_manager.is_tool_connected(agent_id)
            logger.info(f"调试: agent_id={agent_id}, tool_connected={tool_connected}")
            logger.info(f"调试: tool_connections={list(connection_manager.tool_connections.keys())}")
            logger.info(f"调试: sse_tool_connections={list(connection_manager.sse_tool_connections.keys())}")
            
            if not tool_connected:
                logger.warning(f"工具端未连接: {agent_id}")
                # 发送JSON-RPC格式的错误消息给客户端
                error_message = create_tool_not_connected_error(request_id, agent_id)
                await connection_manager.forward_to_robot_by_uuid(
                    connection_uuid, error_message
                )
                return

            # 转发转换后的消息给工具端
            success = await connection_manager.forward_to_tool(
                agent_id, transformed_message
            )
            if not success:
                # 尝试转发给SSE工具
                sse_success = await sse_handler.send_mcp_request_to_sse(
                    agent_id, transformed_message
                )
                if not sse_success:
                    logger.error(f"转发消息给工具端失败: {agent_id}")
                    # 发送JSON-RPC格式的错误消息给客户端
                    error_message = create_forward_failed_error(request_id, agent_id)
                    await connection_manager.forward_to_robot_by_uuid(
                        connection_uuid, error_message
                    )

        except json.JSONDecodeError:
            logger.error(f"客户端消息格式错误: {message}")
        except Exception as e:
            logger.error(f"处理客户端消息时发生错误: {e}")


# 全局WebSocket处理器实例
websocket_handler = WebSocketHandler()
