#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SSE工具的客户端
"""

import asyncio
import websockets
import json
import logging
import time

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SSEToolClient')

async def test_sse_tool():
    """测试SSE工具"""
    endpoint_url = "ws://192.168.6.237:8004"
    agent_id = "3ec0027f77724376b50a9842ed39fd79"  # 使用与SSE工具一致的agent_id
    token = "1Uat87sJM%2BC00BXdXEAogrA3TfvWAhXFSB31pEdgb2hWvVisL7/SIo%2BbTY4iqMHN"  # 使用正确的token
    
    # 构建WebSocket URL
    ws_url = f"{endpoint_url}/mcp_endpoint/call/?token={token}"
    logger.info(f"连接到WebSocket端点: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info("WebSocket连接已建立")
            
            # 等待一下，让SSE工具有时间注册
            logger.info("等待SSE工具注册...")
            await asyncio.sleep(3)
            
            # 测试获取工具列表
            logger.info("=== 测试获取工具列表 ===")
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": "list_tools_1",
                "method": "tools/list"
            }
            
            await websocket.send(json.dumps(list_tools_request))
            logger.info("已发送工具列表请求")
            
            # 接收响应
            response = await websocket.recv()
            logger.info(f"收到工具列表响应: {response}")
            
            # 测试计算器工具
            logger.info("=== 测试计算器工具 ===")
            calculator_request = {
                "jsonrpc": "2.0",
                "id": "calc_1",
                "method": "tools/call",
                "params": {
                    "name": "my_calculator",  # 使用正确的工具名称
                    "arguments": {
                        "expression": "2 + 3 * 4"
                    }
                }
            }
            
            await websocket.send(json.dumps(calculator_request))
            logger.info("已发送计算器请求: 2 + 3 * 4")
            
            # 接收响应
            response = await websocket.recv()
            logger.info(f"收到计算器响应: {response}")
            
            # 测试获取时间工具
            logger.info("=== 测试获取时间工具 ===")
            time_request = {
                "jsonrpc": "2.0",
                "id": "time_1",
                "method": "tools/call",
                "params": {
                    "name": "get_time",
                    "arguments": {}
                }
            }
            
            await websocket.send(json.dumps(time_request))
            logger.info("已发送获取时间请求")
            
            # 接收响应
            response = await websocket.recv()
            logger.info(f"收到时间响应: {response}")
            
            logger.info("=== 测试完成 ===")
            
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")

if __name__ == "__main__":
    asyncio.run(test_sse_tool())


