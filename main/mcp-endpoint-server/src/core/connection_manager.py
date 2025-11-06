"""
连接管理器
负责管理WebSocket连接和消息转发
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed
from ..utils.logger import get_logger

logger = get_logger()


class RobotConnection:
    """客户端连接信息"""

    def __init__(self, websocket: WebSocketServerProtocol, agent_id: str):
        self.websocket = websocket
        self.agent_id = agent_id
        self.connection_uuid = str(uuid.uuid4())
        self.timestamp = time.time()


class SSEConnection:
    """SSE连接信息"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.sse_id = str(uuid.uuid4())
        self.timestamp = time.time()
        self.message_queue = asyncio.Queue()
        self.is_active = True


class ConnectionManager:
    """连接管理器"""

    def __init__(self):
        # 工具端连接: {agentId: websocket}
        self.tool_connections: Dict[str, WebSocketServerProtocol] = {}
        # SSE工具端连接: {agentId: sse_id}
        self.sse_tool_connections: Dict[str, str] = {}
        # 客户端连接: {connection_uuid: RobotConnection}
        self.robot_connections: Dict[str, RobotConnection] = {}
        # SSE连接: {sse_id: SSEConnection}
        self.sse_connections: Dict[str, SSEConnection] = {}
        # 连接时间戳: {agentId: timestamp}
        self.connection_timestamps: Dict[str, float] = {}
        # 连接锁
        self._lock = asyncio.Lock()

    async def register_tool_connection(
        self, agent_id: str, websocket: WebSocketServerProtocol
    ):
        """注册工具端连接"""
        async with self._lock:
            # 如果已存在连接，先关闭旧连接
            if agent_id in self.tool_connections:
                old_websocket = self.tool_connections[agent_id]
                try:
                    await old_websocket.close(1000, "新连接替换")
                except Exception as e:
                    logger.warning(f"关闭旧工具端连接失败: {e}")

            self.tool_connections[agent_id] = websocket
            self.connection_timestamps[agent_id] = time.time()
            logger.info(f"工具端连接已注册: {agent_id}")

    async def register_sse_tool_connection(self, agent_id: str, sse_id: str):
        """注册SSE工具端连接"""
        async with self._lock:
            # 如果已存在连接，先清理旧连接
            if agent_id in self.sse_tool_connections:
                old_sse_id = self.sse_tool_connections[agent_id]
                logger.info(f"替换旧的SSE工具连接: {agent_id} (旧SSE ID: {old_sse_id})")

            self.sse_tool_connections[agent_id] = sse_id
            self.connection_timestamps[agent_id] = time.time()
            logger.info(f"SSE工具端连接已注册: {agent_id} (SSE ID: {sse_id})")

    async def register_robot_connection(
        self, agent_id: str, websocket: WebSocketServerProtocol
    ) -> str:
        """注册客户端连接，返回分配的UUID"""
        async with self._lock:
            robot_conn = RobotConnection(websocket, agent_id)
            self.robot_connections[robot_conn.connection_uuid] = robot_conn
            self.connection_timestamps[agent_id] = time.time()
            logger.info(
                f"客户端连接已注册: {agent_id}, UUID: {robot_conn.connection_uuid}"
            )
            return robot_conn.connection_uuid

    async def unregister_tool_connection(self, agent_id: str):
        """注销工具端连接"""
        async with self._lock:
            if agent_id in self.tool_connections:
                del self.tool_connections[agent_id]
                if agent_id in self.connection_timestamps:
                    del self.connection_timestamps[agent_id]
                logger.info(f"工具端连接已注销: {agent_id}")

    async def unregister_sse_tool_connection(self, agent_id: str):
        """注销SSE工具端连接"""
        async with self._lock:
            if agent_id in self.sse_tool_connections:
                sse_id = self.sse_tool_connections[agent_id]
                del self.sse_tool_connections[agent_id]
                if agent_id in self.connection_timestamps:
                    del self.connection_timestamps[agent_id]
                logger.info(f"SSE工具端连接已注销: {agent_id} (SSE ID: {sse_id})")

    async def unregister_robot_connection(self, connection_uuid: str):
        """注销客户端连接"""
        async with self._lock:
            if connection_uuid in self.robot_connections:
                robot_conn = self.robot_connections[connection_uuid]
                del self.robot_connections[connection_uuid]
                logger.info(
                    f"客户端连接已注销: {robot_conn.agent_id}, UUID: {connection_uuid}"
                )

    async def register_sse_connection(self, agent_id: str) -> str:
        """注册SSE连接，返回SSE连接ID"""
        async with self._lock:
            sse_conn = SSEConnection(agent_id)
            self.sse_connections[sse_conn.sse_id] = sse_conn
            self.connection_timestamps[agent_id] = time.time()
            logger.info(f"SSE连接已注册: {agent_id}, SSE ID: {sse_conn.sse_id}")
            return sse_conn.sse_id

    async def unregister_sse_connection(self, sse_id: str):
        """注销SSE连接"""
        async with self._lock:
            if sse_id in self.sse_connections:
                sse_conn = self.sse_connections[sse_id]
                sse_conn.is_active = False
                del self.sse_connections[sse_id]
                logger.info(f"SSE连接已注销: {sse_conn.agent_id}, SSE ID: {sse_id}")

    def is_sse_connected(self, sse_id: str) -> bool:
        """检查SSE连接是否仍然有效"""
        return sse_id in self.sse_connections and self.sse_connections[sse_id].is_active

    async def get_sse_message(self, sse_id: str, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """获取SSE消息，带超时"""
        if sse_id not in self.sse_connections:
            return None
        
        sse_conn = self.sse_connections[sse_id]
        try:
            return await asyncio.wait_for(sse_conn.message_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def send_sse_message(self, sse_id: str, message: Dict[str, Any]):
        """发送消息到SSE连接"""
        if sse_id in self.sse_connections:
            sse_conn = self.sse_connections[sse_id]
            if sse_conn.is_active:
                await sse_conn.message_queue.put(message)
                logger.debug(f"SSE消息已发送: {sse_id} - {message}")

    async def send_sse_message_to_agent(self, agent_id: str, message: Dict[str, Any]):
        """发送消息到指定agent的所有SSE连接"""
        async with self._lock:
            for sse_conn in self.sse_connections.values():
                if sse_conn.agent_id == agent_id and sse_conn.is_active:
                    await sse_conn.message_queue.put(message)
                    logger.debug(f"SSE消息已发送到agent {agent_id}: {message}")

    def _transform_jsonrpc_id(self, original_id: Any, connection_uuid: str) -> str:
        """转换JSON-RPC ID"""
        if isinstance(original_id, int):
            return f"{connection_uuid}_n_{original_id}"
        elif isinstance(original_id, str):
            return f"{connection_uuid}_s_{original_id}"
        else:
            # 其他类型转换为字符串
            return f"{connection_uuid}_s_{str(original_id)}"

    def _restore_jsonrpc_id(self, transformed_id: str) -> Tuple[Optional[str], Any]:
        """还原JSON-RPC ID，返回(connection_uuid, original_id)"""
        logger.info(f"尝试还原JSON-RPC ID: {transformed_id}")
        
        if not transformed_id or "_" not in transformed_id:
            logger.info(f"ID格式不正确，无法还原: {transformed_id}")
            return None, None

        # 解析格式: uuid_type_original_id
        parts = transformed_id.split("_", 2)
        if len(parts) < 3:
            logger.info(f"ID部分不足，无法还原: {parts}")
            return None, None

        connection_uuid = parts[0]
        id_type = parts[1]
        original_id_part = parts[2]
        
        logger.info(f"解析结果: connection_uuid={connection_uuid}, id_type={id_type}, original_id_part={original_id_part}")

        # 检查connection_uuid是否是有效的UUID格式
        # UUID格式: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        if len(connection_uuid) != 36 or connection_uuid.count('-') != 4:
            logger.info(f"connection_uuid不是有效的UUID格式: {connection_uuid}")
            return None, None

        if id_type == "n":
            # 数字类型
            try:
                original_id = int(original_id_part)
            except ValueError:
                original_id = original_id_part
        elif id_type == "s":
            # 字符串类型
            if original_id_part == "null":
                original_id = None
            else:
                original_id = original_id_part
        else:
            # 未知类型，保持原样
            original_id = original_id_part

        return connection_uuid, original_id

    def transform_jsonrpc_message(
        self, message: Dict[str, Any], connection_uuid: str
    ) -> Dict[str, Any]:
        """转换JSON-RPC消息的ID"""
        if not isinstance(message, dict):
            return message

        # 创建消息副本
        transformed_message = message.copy()

        # 转换ID
        if "id" in transformed_message:
            original_id = transformed_message["id"]
            if original_id:
                transformed_message["id"] = self._transform_jsonrpc_id(
                    original_id, connection_uuid
                )

        return transformed_message

    def restore_jsonrpc_message(
        self, message: Dict[str, Any]
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """还原JSON-RPC消息的ID，返回(connection_uuid, restored_message)"""
        if not isinstance(message, dict):
            return None, message

        # 创建消息副本
        restored_message = message.copy()

        # 还原ID
        if "id" in restored_message:
            transformed_id = restored_message["id"]
            connection_uuid, original_id = self._restore_jsonrpc_id(transformed_id)
            if connection_uuid:
                restored_message["id"] = original_id
                return connection_uuid, restored_message

        return None, restored_message

    async def forward_to_tool(self, agent_id: str, message: Any) -> bool:
        """转发消息给工具端（WebSocket或SSE）"""
        async with self._lock:
            logger.info(f"forward_to_tool调试: agent_id={agent_id}")
            logger.info(f"forward_to_tool调试: tool_connections={list(self.tool_connections.keys())}")
            logger.info(f"forward_to_tool调试: sse_tool_connections={list(self.sse_tool_connections.keys())}")
            logger.info(f"forward_to_tool调试: agent_id in tool_connections={agent_id in self.tool_connections}")
            logger.info(f"forward_to_tool调试: agent_id in sse_tool_connections={agent_id in self.sse_tool_connections}")
            
            # 首先尝试WebSocket工具连接
            if agent_id in self.tool_connections:
                websocket = self.tool_connections[agent_id]
                try:
                    # 确保消息是字符串格式
                    if isinstance(message, dict):
                        message_str = json.dumps(message, ensure_ascii=False)
                    elif isinstance(message, str):
                        message_str = message
                    else:
                        message_str = str(message)

                    await websocket.send_text(message_str)
                    logger.debug(f"消息已转发给WebSocket工具端 {agent_id}: {message_str[:100]}...")
                    return True
                except ConnectionClosed:
                    logger.warning(f"WebSocket工具端连接已关闭: {agent_id}")
                    await self.unregister_tool_connection(agent_id)
                    return False
                except Exception as e:
                    logger.error(f"转发消息给WebSocket工具端失败: {e}")
                    return False
            
            # 然后尝试SSE工具连接
            elif agent_id in self.sse_tool_connections:
                sse_id = self.sse_tool_connections[agent_id]
                try:
                    # 确保消息是字典格式
                    if isinstance(message, str):
                        message_dict = json.loads(message)
                    elif isinstance(message, dict):
                        message_dict = message
                    else:
                        message_dict = {"raw_message": str(message)}

                    # 按照SSE处理器期望的格式包装消息
                    sse_message = {
                        "type": "mcp_request",
                        "mcp_message": message_dict,
                        "timestamp": time.time()
                    }

                    await self.send_sse_message(sse_id, sse_message)
                    logger.debug(f"消息已转发给SSE工具端 {agent_id}: {str(sse_message)[:100]}...")
                    return True
                except Exception as e:
                    logger.error(f"转发消息给SSE工具端失败: {e}")
                    return False
            
            else:
                logger.warning(f"工具端连接不存在: {agent_id}")
                return False

    async def forward_to_robot_by_uuid(
        self, connection_uuid: str, message: Any
    ) -> bool:
        """根据UUID转发消息给特定的客户端连接"""
        async with self._lock:
            if connection_uuid not in self.robot_connections:
                logger.warning(f"客户端连接不存在: {connection_uuid}")
                return False

            robot_conn = self.robot_connections[connection_uuid]
            try:
                # 确保消息是字符串格式
                if isinstance(message, dict):
                    message_str = json.dumps(message, ensure_ascii=False)
                elif isinstance(message, str):
                    message_str = message
                else:
                    message_str = str(message)

                await robot_conn.websocket.send_text(message_str)
                logger.debug(
                    f"消息已转发给客户端 {robot_conn.agent_id} (UUID: {connection_uuid}): {message_str[:100]}..."
                )
                return True
            except ConnectionClosed:
                logger.warning(f"客户端连接已关闭: {connection_uuid}")
                await self.unregister_robot_connection(connection_uuid)
                return False
            except Exception as e:
                logger.error(f"转发消息给客户端失败: {e}")
                return False

    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        # 统计每个agent_id的连接数
        agent_connection_counts = {}
        for robot_conn in self.robot_connections.values():
            agent_id = robot_conn.agent_id
            agent_connection_counts[agent_id] = (
                agent_connection_counts.get(agent_id, 0) + 1
            )

        # 统计SSE连接
        sse_agent_counts = {}
        for sse_conn in self.sse_connections.values():
            agent_id = sse_conn.agent_id
            sse_agent_counts[agent_id] = (
                sse_agent_counts.get(agent_id, 0) + 1
            )

        return {
            "tool_connections": len(self.tool_connections) + len(self.sse_tool_connections),
            "robot_connections": len(self.robot_connections),
            "sse_connections": len(self.sse_connections),
            "total_connections": len(self.tool_connections)
            + len(self.sse_tool_connections)
            + len(self.robot_connections)
            + len(self.sse_connections),
            "robot_connections_by_agent": agent_connection_counts,
            "sse_connections_by_agent": sse_agent_counts,
        }

    def is_tool_connected(self, agent_id: str) -> bool:
        """检查工具端是否已连接（WebSocket或SSE）"""
        return agent_id in self.tool_connections or agent_id in self.sse_tool_connections

    def is_robot_connected(self, agent_id: str) -> bool:
        """检查客户端是否已连接"""
        return any(
            conn.agent_id == agent_id for conn in self.robot_connections.values()
        )

    def get_robot_connections_by_agent(self, agent_id: str) -> List[RobotConnection]:
        """获取指定agent_id的所有客户端连接"""
        return [
            conn
            for conn in self.robot_connections.values()
            if conn.agent_id == agent_id
        ]


# 全局连接管理器实例
connection_manager = ConnectionManager()
