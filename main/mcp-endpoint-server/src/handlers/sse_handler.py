"""
SSE处理器
处理SSE工具连接和消息转换
"""

import json
import asyncio
from typing import Dict, Any, Optional
from ..core.connection_manager import connection_manager
from ..utils.logger import get_logger
from ..utils.jsonrpc import (
    create_tool_not_connected_error,
    create_forward_failed_error,
)

logger = get_logger()


class SSEHandler:
    """SSE处理器"""

    def __init__(self):
        pass

    async def handle_sse_message(self, agent_id: str, sse_id: str, message: Dict[str, Any]):
        """处理来自SSE工具的消息"""
        try:
            logger.debug(f"收到SSE工具消息: {agent_id} (SSE ID: {sse_id}) - {message}")
            
            # 检查消息结构，可能是包装后的格式
            if "message" in message and "sse_id" in message:
                # 解包消息：{sse_id: ..., message: {...}}
                actual_message = message["message"]
                logger.debug(f"解包SSE消息: {actual_message}")
            else:
                # 直接消息格式：{type: ..., mcp_message: ...}
                actual_message = message
            
            # 检查消息类型
            message_type = actual_message.get("type", "")
            
            if message_type == "mcp_request":
                # 处理MCP请求，转发给WebSocket工具端
                await self._handle_mcp_request(agent_id, sse_id, actual_message)
            elif message_type == "mcp_response":
                # 处理MCP响应，转发给客户端
                await self._handle_mcp_response(agent_id, sse_id, actual_message)
            elif message_type == "heartbeat":
                # 处理心跳消息
                await self._handle_heartbeat(agent_id, sse_id, actual_message)
            elif "method" in actual_message and actual_message.get("jsonrpc") == "2.0":
                # 处理MCP通知消息（如notifications/initialized）
                await self._handle_mcp_notification(agent_id, sse_id, actual_message)
            else:
                logger.warning(f"未知的SSE消息类型: {message_type}, 消息内容: {actual_message}")
                logger.warning(f"消息键: {list(actual_message.keys())}")
                logger.warning(f"消息类型检查: type={message_type}, has_method={'method' in actual_message}, jsonrpc={actual_message.get('jsonrpc')}")
                
        except Exception as e:
            logger.error(f"处理SSE消息时发生错误: {e}")

    async def _handle_mcp_request(self, agent_id: str, sse_id: str, message: Dict[str, Any]):
        """处理MCP请求，转发给WebSocket工具端"""
        try:
            # 检查是否有对应的WebSocket工具端连接
            if not connection_manager.is_tool_connected(agent_id):
                logger.warning(f"WebSocket工具端未连接: {agent_id}")
                # 发送错误消息回SSE
                error_message = {
                    "type": "mcp_error",
                    "error": f"WebSocket工具端未连接: {agent_id}",
                    "sse_id": sse_id
                }
                await connection_manager.send_sse_message(sse_id, error_message)
                return

            # 提取MCP消息
            mcp_message = message.get("mcp_message", {})
            if not mcp_message:
                logger.warning("SSE消息中缺少MCP消息")
                return

            # 转换JSON-RPC ID以支持多连接
            transformed_message = connection_manager.transform_jsonrpc_message(
                mcp_message, f"sse_{sse_id}"
            )

            # 转发给WebSocket工具端
            success = await connection_manager.forward_to_tool(agent_id, transformed_message)
            if not success:
                logger.error(f"转发MCP请求给WebSocket工具端失败: {agent_id}")
                error_message = {
                    "type": "mcp_error",
                    "error": f"转发消息失败: {agent_id}",
                    "sse_id": sse_id
                }
                await connection_manager.send_sse_message(sse_id, error_message)

        except Exception as e:
            logger.error(f"处理MCP请求时发生错误: {e}")

    async def _handle_mcp_response(self, agent_id: str, sse_id: str, message: Dict[str, Any]):
        """处理MCP响应，转发给客户端"""
        try:
            # 提取MCP消息
            mcp_message = message.get("mcp_message", {})
            if not mcp_message:
                logger.warning("SSE消息中缺少MCP消息")
                return

            # 还原JSON-RPC ID
            logger.info(f"尝试还原JSON-RPC消息: {mcp_message}")
            connection_uuid, restored_message = connection_manager.restore_jsonrpc_message(mcp_message)
            logger.info(f"还原结果: connection_uuid={connection_uuid}, restored_message={restored_message}")
            
            if connection_uuid:
                # 转发给特定的客户端连接
                success = await connection_manager.forward_to_robot_by_uuid(connection_uuid, restored_message)
                if not success:
                    logger.error(f"转发MCP响应给客户端失败: {connection_uuid}")
            else:
                # 无法还原ID，可能是SSE工具主动发送的消息（如工具列表）
                # 转发给该agent的所有客户端连接
                logger.info(f"SSE工具主动发送消息，转发给agent {agent_id} 的所有客户端")
                robot_connections = connection_manager.get_robot_connections_by_agent(agent_id)
                if robot_connections:
                    for robot_conn in robot_connections:
                        success = await connection_manager.forward_to_robot_by_uuid(robot_conn.connection_uuid, mcp_message)
                        if success:
                            logger.info(f"消息已转发给客户端: {robot_conn.connection_uuid}")
                        else:
                            logger.error(f"转发消息给客户端失败: {robot_conn.connection_uuid}")
                else:
                    logger.warning(f"没有找到agent {agent_id} 的客户端连接")

        except Exception as e:
            logger.error(f"处理MCP响应时发生错误: {e}")

    async def _handle_heartbeat(self, agent_id: str, sse_id: str, message: Dict[str, Any]):
        """处理心跳消息"""
        logger.debug(f"收到SSE心跳: {agent_id} (SSE ID: {sse_id})")
        # 心跳消息通常不需要特殊处理，只是保持连接活跃

    async def _handle_mcp_notification(self, agent_id: str, sse_id: str, message: Dict[str, Any]):
        """处理MCP通知消息"""
        try:
            method = message.get("method", "")
            logger.debug(f"收到SSE MCP通知: {agent_id} (SSE ID: {sse_id}) - {method}")
            
            if method == "notifications/initialized":
                # 初始化完成通知，不需要特殊处理
                logger.info(f"SSE工具初始化完成: {agent_id}")
            else:
                logger.debug(f"未处理的MCP通知: {method}")
                
        except Exception as e:
            logger.error(f"处理MCP通知时发生错误: {e}")

    async def send_mcp_request_to_sse(self, agent_id: str, mcp_message: Dict[str, Any]):
        """发送MCP请求到SSE工具"""
        try:
            # 查找该agent的所有SSE连接
            sse_connections = [
                sse_conn for sse_conn in connection_manager.sse_connections.values()
                if sse_conn.agent_id == agent_id and sse_conn.is_active
            ]

            if not sse_connections:
                logger.warning(f"没有找到agent {agent_id} 的SSE连接")
                return False

            # 发送消息到所有SSE连接
            sse_message = {
                "type": "mcp_request",
                "mcp_message": mcp_message,
                "timestamp": asyncio.get_event_loop().time()
            }

            for sse_conn in sse_connections:
                await connection_manager.send_sse_message(sse_conn.sse_id, sse_message)

            return True

        except Exception as e:
            logger.error(f"发送MCP请求到SSE工具失败: {e}")
            return False

    async def send_mcp_response_to_sse(self, agent_id: str, mcp_message: Dict[str, Any]):
        """发送MCP响应到SSE工具"""
        try:
            # 查找该agent的所有SSE连接
            sse_connections = [
                sse_conn for sse_conn in connection_manager.sse_connections.values()
                if sse_conn.agent_id == agent_id and sse_conn.is_active
            ]

            if not sse_connections:
                logger.warning(f"没有找到agent {agent_id} 的SSE连接")
                return False

            # 发送消息到所有SSE连接
            sse_message = {
                "type": "mcp_response",
                "mcp_message": mcp_message,
                "timestamp": asyncio.get_event_loop().time()
            }

            for sse_conn in sse_connections:
                await connection_manager.send_sse_message(sse_conn.sse_id, sse_message)

            return True

        except Exception as e:
            logger.error(f"发送MCP响应到SSE工具失败: {e}")
            return False


# 全局SSE处理器实例
sse_handler = SSEHandler()
