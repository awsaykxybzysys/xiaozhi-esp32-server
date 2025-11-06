#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多个agent_id的脚本
"""

import asyncio
import aiohttp
import json
import logging
import time
from token_manager import TokenManager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MultiAgentTest')

async def test_websocket_client(agent_id: str, token: str):
    """测试WebSocket客户端连接"""
    endpoint_url = "ws://192.168.1.203:8004"
    ws_url = f"{endpoint_url}/mcp_endpoint/call/?token={token}"
    
    logger.info(f"=== 测试Agent {agent_id} 的WebSocket连接 ===")
    logger.info(f"连接到: {ws_url}")
    
    try:
        import websockets
        async with websockets.connect(ws_url) as websocket:
            logger.info(f"✅ WebSocket连接已建立: {agent_id}")
            
            # 等待一下让SSE工具注册
            await asyncio.sleep(2)
            
            # 测试获取工具列表
            tools_request = {
                "jsonrpc": "2.0",
                "id": f"list_tools_{agent_id}_{int(time.time())}",
                "method": "tools/list"
            }
            
            await websocket.send(json.dumps(tools_request))
            logger.info(f"已发送工具列表请求: {agent_id}")
            
            # 接收响应
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            response_data = json.loads(response)
            
            if response_data.get("result"):
                tools = response_data["result"].get("tools", [])
                logger.info(f"✅ {agent_id} 工具列表: {[tool['name'] for tool in tools]}")
                
                # 测试调用计算器工具
                if tools:
                    tool_name = tools[0]["name"]
                    calc_request = {
                        "jsonrpc": "2.0",
                        "id": f"calc_{agent_id}_{int(time.time())}",
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": {
                                "expression": f"10 + {hash(agent_id) % 100}"
                            }
                        }
                    }
                    
                    await websocket.send(json.dumps(calc_request))
                    logger.info(f"已发送计算器请求: {agent_id}")
                    
                    # 接收响应
                    calc_response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    calc_data = json.loads(calc_response)
                    
                    if calc_data.get("result"):
                        logger.info(f"✅ {agent_id} 计算器响应: {calc_data['result']}")
                    else:
                        logger.error(f"❌ {agent_id} 计算器调用失败: {calc_data.get('error')}")
            else:
                logger.error(f"❌ {agent_id} 获取工具列表失败: {response_data.get('error')}")
                
    except Exception as e:
        logger.error(f"❌ {agent_id} WebSocket测试失败: {e}")

async def main():
    """主函数"""
    logger.info("=== 开始多Agent测试 ===")
    
    # 创建Token管理器
    token_manager = TokenManager()
    
    # 定义多个agent_id
    agent_ids = [
        "agent_001",
        "agent_002", 
        "agent_003",
        "test_agent_123"
    ]
    
    # 为每个agent生成token
    logger.info("=== 生成多个Agent的Token ===")
    tokens = {}
    for agent_id in agent_ids:
        token = await token_manager.generate_token(agent_id)
        if token:
            tokens[agent_id] = token
            logger.info(f"✅ {agent_id}: {token[:50]}...")
        else:
            logger.error(f"❌ {agent_id}: 生成token失败")
    
    logger.info(f"✅ 成功为 {len(tokens)} 个Agent生成了Token")
    
    # 测试每个agent的WebSocket连接
    logger.info("=== 开始WebSocket连接测试 ===")
    tasks = []
    for agent_id, token in tokens.items():
        task = asyncio.create_task(test_websocket_client(agent_id, token))
        tasks.append(task)
    
    # 等待所有测试完成
    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("=== 多Agent测试完成 ===")

if __name__ == "__main__":
    asyncio.run(main())
