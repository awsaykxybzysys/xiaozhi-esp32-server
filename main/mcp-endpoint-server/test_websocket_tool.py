#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试WebSocket工具连接
"""

import asyncio
import websockets
import json
import logging
import time

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('WebSocketTool')

async def test_websocket_tool():
    """测试WebSocket工具连接"""
    endpoint_url = "ws://192.168.6.237:8004"
    agent_id = "single_module"
    token = "2ZberFvI%2B/65Rk3BMmfctyfW8dNHZPvaP9r7gRxEDRM%3D"
    
    # 构建WebSocket URL
    ws_url = f"{endpoint_url}/mcp_endpoint/mcp/?token={token}"
    logger.info(f"连接到WebSocket工具端点: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info("WebSocket工具连接已建立")
            
            # 等待一下，让连接注册完成
            await asyncio.sleep(1)
            
            # 发送工具列表响应
            logger.info("=== 发送工具列表响应 ===")
            tools_response = {
                "jsonrpc": "2.0",
                "id": f"tools_list_{int(time.time())}",
                "result": {
                    "tools": [
                        {
                            "name": "test_calculator",
                            "description": "测试计算器",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "expression": {
                                        "type": "string",
                                        "description": "要计算的数学表达式"
                                    }
                                },
                                "required": ["expression"]
                            }
                        }
                    ]
                }
            }
            
            await websocket.send(json.dumps(tools_response))
            logger.info("工具列表响应已发送")
            
            # 保持连接并处理消息
            logger.info("等待客户端消息...")
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    logger.info(f"收到消息: {message}")
                    
                    # 解析消息
                    try:
                        data = json.loads(message)
                        method = data.get('method')
                        
                        if method == 'tools/call':
                            # 处理工具调用
                            params = data.get('params', {})
                            tool_name = params.get('name')
                            tool_args = params.get('arguments', {})
                            
                            logger.info(f"处理工具调用: {tool_name} with args: {tool_args}")
                            
                            # 发送响应
                            response = {
                                "jsonrpc": "2.0",
                                "id": data.get('id'),
                                "result": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": f"工具 {tool_name} 执行成功，参数: {tool_args}"
                                        }
                                    ]
                                }
                            }
                            
                            await websocket.send(json.dumps(response))
                            logger.info("工具调用响应已发送")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"解析消息失败: {e}")
                        
                except asyncio.TimeoutError:
                    logger.info("等待消息超时，发送心跳")
                    # 发送心跳
                    heartbeat = {
                        "jsonrpc": "2.0",
                        "id": f"heartbeat_{int(time.time())}",
                        "method": "ping"
                    }
                    await websocket.send(json.dumps(heartbeat))
                    
    except Exception as e:
        logger.error(f"WebSocket工具连接出错: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_tool())





