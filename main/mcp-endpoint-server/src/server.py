"""
MCP Endpoint Server
主服务器文件
"""

import sys
import json
import signal
import time
import asyncio
import uvicorn
from urllib.parse import quote
from .utils.config import config
from .utils.logger import get_logger
from .utils.aes_utils import decrypt, encrypt
from .utils.jsonrpc import (
    JSONRPCProtocol,
)
from src.utils.util import get_local_ip
from .utils import __version__
from contextlib import asynccontextmanager
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from .core.connection_manager import connection_manager
from .handlers.websocket_handler import websocket_handler
from .handlers.sse_handler import sse_handler
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse

logger = get_logger()


async def validate_token_and_get_agent_id(websocket: WebSocket) -> str:
    """
    验证token并获取agentId的公共方法

    Args:
        websocket: WebSocket连接对象

    Returns:
        str: 验证成功返回agentId，失败返回None
    """
    token = websocket.query_params.get("token")
    if not token:
        logger.error("缺少token参数")
        await websocket.close(code=1008, reason="缺少token参数")
        return None

    data = decrypt(config.get("server", "key", ""), token)
    if not data:
        logger.error(f"token解密失败: {token}")
        await websocket.close(code=1008, reason="token解密失败")
        return None

    try:
        data = json.loads(data)
        agent_id = data.get("agentId")
        if not agent_id:
            logger.error("无对应agentId")
            await websocket.close(code=1008, reason="无对应agentId")
            return None
        return agent_id
    except json.JSONDecodeError:
        logger.error("token数据格式错误")
        await websocket.close(code=1008, reason="token数据格式错误")
        return None


async def validate_token_and_get_agent_id_from_request(request: Request) -> str:
    """
    从HTTP请求中验证token并获取agentId的公共方法

    Args:
        request: HTTP请求对象

    Returns:
        str: 验证成功返回agentId，失败返回None
    """
    # 尝试多种方式获取token
    token = request.query_params.get("token")
    if not token:
        # 尝试从URL中直接解析
        url = str(request.url)
        logger.info(f"DEBUG: 完整URL: {url}")
        if "token=" in url:
            token_part = url.split("token=")[1]
            if "&" in token_part:
                token = token_part.split("&")[0]
            else:
                token = token_part
            logger.info(f"DEBUG: 从URL解析的token: {token}")
    
    logger.info(f"DEBUG: 最终token参数: {token}")
    logger.info(f"DEBUG: 所有查询参数: {dict(request.query_params)}")
    if not token:
        logger.error("缺少token参数")
        return None

    data = decrypt(config.get("server", "key", ""), token)
    if not data:
        logger.error(f"token解密失败: {token}")
        return None

    try:
        data = json.loads(data)
        agent_id = data.get("agentId")
        if not agent_id:
            logger.error("无对应agentId")
            return None
        return agent_id
    except json.JSONDecodeError:
        logger.error("token数据格式错误")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("MCP Endpoint Server 正在启动...")
    logger.info(f"=====下面的地址分别是智控台/单模块MCP接入点地址====")
    local_ip = get_local_ip()
    logger.info(
        f"智控台MCP参数配置: http://{local_ip}:{config.getint('server', 'port', 8004)}/mcp_endpoint/health?key={config.get('server', 'key', '')}"
    )
    encrypted_token = encrypt(
        config.get("server", "key", ""), '{"agentId":"3538bde8a5504f3a8a504c161fdba08d"}'
    )
    token = quote(encrypted_token)
    logger.info(
        f"单模块部署MCP接入点: ws://{local_ip}:{config.getint('server', 'port', 8004)}/mcp_endpoint/mcp/?token={token}"
    )
    logger.info(
        "=====请根据具体部署选择使用，请勿泄露给任何人======",
    )
    yield
    # 关闭时
    logger.info("MCP Endpoint Server 已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="MCP Endpoint Server",
    description="高效的WebSocket中转服务器",
    version=__version__,
    lifespan=lifespan,
)

# 配置CORS
if config.getboolean("security", "enable_cors", True):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.get("security", "allowed_origins", "*")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
async def redirect_root():
    """根路径重定向到 /mcp_endpoint/"""
    return RedirectResponse(url="/mcp_endpoint/")


@app.get("/mcp_endpoint/")
async def root():
    """根路径"""
    response = JSONRPCProtocol.create_success_response(
        result={
            "message": "MCP Endpoint Server",
            "version": __version__,
            "status": "running",
        }
    )
    return JSONRPCProtocol.to_dict(response)


@app.get("/mcp_endpoint/health")
async def health_check(key: str = None):
    """健康检查"""
    # 验证key参数
    expected_key = config.get("server", "key", "")
    if not key or key != expected_key:
        response = JSONRPCProtocol.create_error_response(
            error_code=JSONRPCProtocol.AUTHENTICATION_ERROR,
            error_message="密钥验证失败",
            error_data={"details": "提供的密钥无效或缺失"},
        )
        return JSONRPCProtocol.to_dict(response)

    stats = connection_manager.get_connection_stats()
    response = JSONRPCProtocol.create_success_response(
        result={"status": "success", "connections": stats}
    )
    return JSONRPCProtocol.to_dict(response)


@app.websocket("/mcp_endpoint/mcp/")
async def websocket_tool_endpoint(websocket: WebSocket):
    """工具端WebSocket端点"""
    await websocket.accept()

    # 获取agentId参数
    agent_id = await validate_token_and_get_agent_id(websocket)
    if not agent_id:
        return

    try:
        # 注册连接
        await connection_manager.register_tool_connection(agent_id, websocket)
        logger.info(f"工具端连接已建立: {agent_id}")

        # 处理消息
        while True:
            try:
                message = await websocket.receive_text()
                await websocket_handler._handle_tool_message(agent_id, message)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"处理工具端消息时发生错误: {e}")
                break

    except Exception as e:
        logger.error(f"处理工具端连接时发生错误: {e}")
    finally:
        await connection_manager.unregister_tool_connection(agent_id)
        logger.info(f"工具端连接已关闭: {agent_id}")


@app.websocket("/mcp_endpoint/call/")
async def websocket_robot_endpoint(websocket: WebSocket):
    """客户端WebSocket端点"""
    await websocket.accept()

    # 获取agentId参数
    agent_id = await validate_token_and_get_agent_id(websocket)
    if not agent_id:
        return

    try:
        # 注册连接并获取UUID
        connection_uuid = await connection_manager.register_robot_connection(
            agent_id, websocket
        )
        logger.info(f"客户端连接已建立: {agent_id} (UUID: {connection_uuid})")

        # 处理消息
        while True:
            try:
                message = await websocket.receive_text()
                await websocket_handler._handle_robot_message(
                    agent_id, message, connection_uuid
                )
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"处理客户端消息时发生错误: {e}")
                break

    except Exception as e:
        logger.error(f"处理客户端连接时发生错误: {e}")
    finally:
        await connection_manager.unregister_robot_connection(connection_uuid)
        logger.info(f"客户端连接已关闭: {agent_id} (UUID: {connection_uuid})")


@app.get("/mcp_endpoint/sse/{agent_id}")
async def sse_tool_endpoint(agent_id: str, request: Request):
    """SSE工具端点"""
    # 验证token
    validated_agent_id = await validate_token_and_get_agent_id_from_request(request)
    logger.info(f"SSE认证调试 - URL agent_id: {agent_id}, validated_agent_id: {validated_agent_id}")
    
    if not validated_agent_id or validated_agent_id != agent_id:
        logger.error(f"SSE认证失败 - URL agent_id: {agent_id}, validated_agent_id: {validated_agent_id}")
        return JSONRPCProtocol.create_error_response(
            error_code=JSONRPCProtocol.AUTHENTICATION_ERROR,
            error_message="认证失败",
            error_data={"details": "无效的token或agentId不匹配"}
        )
    
    # 先注册SSE连接和工具连接
    print(f"DEBUG: 开始注册SSE连接 for agent_id: {agent_id}")
    sse_connection_id = await connection_manager.register_sse_connection(agent_id)
    print(f"DEBUG: SSE连接已注册: {agent_id} (SSE ID: {sse_connection_id})")
    logger.info(f"SSE连接已注册: {agent_id} (SSE ID: {sse_connection_id})")
    
    # 注册SSE工具连接
    print(f"DEBUG: 开始注册SSE工具连接: {agent_id} -> {sse_connection_id}")
    await connection_manager.register_sse_tool_connection(agent_id, sse_connection_id)
    print(f"DEBUG: SSE工具连接已注册: {agent_id} (SSE ID: {sse_connection_id})")
    logger.info(f"SSE工具连接已注册: {agent_id} (SSE ID: {sse_connection_id})")
    
    print(f"DEBUG: SSE工具连接已建立: {agent_id} (SSE ID: {sse_connection_id})")
    logger.info(f"SSE工具连接已建立: {agent_id} (SSE ID: {sse_connection_id})")
    
    # 创建SSE流
    async def sse_generator():
        try:
            
            # 发送连接确认
            yield f"data: {json.dumps({'type': 'connected', 'agent_id': agent_id, 'sse_id': sse_connection_id}, ensure_ascii=False)}\n\n"
            
            # 保持连接并处理消息
            while True:
                try:
                    # 检查连接是否仍然有效
                    if not connection_manager.is_sse_connected(sse_connection_id):
                        break
                    
                    # 获取待发送的消息
                    message = await connection_manager.get_sse_message(sse_connection_id)
                    if message:
                        yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                    else:
                        # 发送心跳
                        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(30)  # 30秒心跳间隔
                        
                except Exception as e:
                    logger.error(f"SSE消息处理错误: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"SSE连接错误: {e}")
    
    # 创建StreamingResponse，并在结束时清理连接
    async def cleanup_on_close():
        try:
            async for chunk in sse_generator():
                yield chunk
        finally:
            # 清理SSE连接
            if sse_connection_id:
                await connection_manager.unregister_sse_connection(sse_connection_id)
                await connection_manager.unregister_sse_tool_connection(agent_id)
                logger.info(f"SSE工具连接已关闭: {agent_id} (SSE ID: {sse_connection_id})")
    
    return StreamingResponse(
        cleanup_on_close(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@app.get("/mcp_endpoint/token/{agent_id}")
async def generate_token_for_agent(agent_id: str, request: Request):
    """为指定agent_id生成token的端点"""
    # 这里可以添加额外的权限验证，比如检查请求来源等
    try:
        # 生成包含指定agent_id的token
        token_data = json.dumps({"agentId": agent_id})
        encrypted_token = encrypt(config.get("server", "key", ""), token_data)
        token = quote(encrypted_token)
        
        return JSONRPCProtocol.create_success_response(
            result={
                "agent_id": agent_id,
                "token": token,
                "websocket_url": f"ws://{get_local_ip()}:{config.getint('server', 'port', 8004)}/mcp_endpoint/call/?token={token}",
                "sse_url": f"http://{get_local_ip()}:{config.getint('server', 'port', 8004)}/mcp_endpoint/sse/{agent_id}?token={token}"
            }
        )
    except Exception as e:
        logger.error(f"生成token时发生错误: {e}")
        return JSONRPCProtocol.create_error_response(
            error_code=JSONRPCProtocol.INTERNAL_ERROR,
            error_message="生成token失败",
            error_data={"details": str(e)}
        )


@app.post("/mcp_endpoint/sse/{agent_id}/message")
async def sse_tool_message_endpoint(agent_id: str, request: Request):
    """SSE工具消息端点，用于接收SSE工具发送的消息"""
    # 验证token
    validated_agent_id = await validate_token_and_get_agent_id_from_request(request)
    if not validated_agent_id or validated_agent_id != agent_id:
        return JSONRPCProtocol.create_error_response(
            error_code=JSONRPCProtocol.AUTHENTICATION_ERROR,
            error_message="认证失败",
            error_data={"details": "无效的token或agentId不匹配"}
        )
    
    try:
        # 获取请求体
        body = await request.json()
        
        # 从请求中获取SSE ID
        sse_id = body.get("sse_id")
        if not sse_id:
            return JSONRPCProtocol.create_error_response(
                error_code=JSONRPCProtocol.INVALID_PARAMS,
                error_message="缺少sse_id参数",
                error_data={"details": "请求中必须包含sse_id"}
            )
        
        # 验证SSE连接是否存在
        if not connection_manager.is_sse_connected(sse_id):
            return JSONRPCProtocol.create_error_response(
                error_code=JSONRPCProtocol.INVALID_PARAMS,
                error_message="SSE连接不存在",
                error_data={"details": f"SSE连接 {sse_id} 不存在或已断开"}
            )
        
        # 处理SSE消息
        await sse_handler.handle_sse_message(agent_id, sse_id, body)
        
        return JSONRPCProtocol.create_success_response(
            result={"status": "success", "message": "SSE消息已处理"}
        )
        
    except Exception as e:
        logger.error(f"处理SSE工具消息时发生错误: {e}")
        return JSONRPCProtocol.create_error_response(
            error_code=JSONRPCProtocol.INTERNAL_ERROR,
            error_message="内部服务器错误",
            error_data={"details": str(e)}
        )


def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"收到信号 {signum}，正在关闭服务器...")
    sys.exit(0)


def main():
    """主函数"""
    # 设置uvicorn日志拦截
    from .utils.logger import logger_manager

    logger_manager.setup_uvicorn_logging()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 获取配置
    host = config.get("server", "host", "127.0.0.1")
    port = config.getint("server", "port", 8004)
    debug = config.getboolean("server", "debug", False)

    logger.info(f"启动MCP Endpoint Server: {host}:{port}")

    # 启动服务器
    uvicorn.run(
        "src.server:app",
        host=host,
        port=port,
        reload=debug,
        log_level=config.get("server", "log_level", "INFO").lower(),
        access_log=False,
        log_config=None,  # 禁用uvicorn默认日志配置
        use_colors=True,  # 启用颜色支持
    )


if __name__ == "__main__":
    main()
