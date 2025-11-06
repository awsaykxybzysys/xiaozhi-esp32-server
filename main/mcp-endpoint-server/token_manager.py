#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token管理器 - 用于管理多个agent_id的token
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Optional

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TokenManager')

class TokenManager:
    """Token管理器"""
    
    def __init__(self, server_url: str = "http://192.168.1.203:8004"):
        self.server_url = server_url
        self.tokens: Dict[str, str] = {}  # agent_id -> token
        
    async def generate_token(self, agent_id: str) -> Optional[str]:
        """为指定agent_id生成token"""
        try:
            url = f"{self.server_url}/mcp_endpoint/token/{agent_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("result"):
                            token = data["result"]["token"]
                            self.tokens[agent_id] = token
                            logger.info(f"✅ 为 {agent_id} 生成token成功")
                            return token
                        else:
                            logger.error(f"❌ 生成token失败: {data.get('error', '未知错误')}")
                    else:
                        logger.error(f"❌ 请求失败: {response.status}")
        except Exception as e:
            logger.error(f"❌ 生成token时发生错误: {e}")
        return None
    
    async def get_token(self, agent_id: str) -> Optional[str]:
        """获取指定agent_id的token，如果不存在则生成"""
        if agent_id in self.tokens:
            return self.tokens[agent_id]
        return await self.generate_token(agent_id)
    
    def get_websocket_url(self, agent_id: str) -> Optional[str]:
        """获取WebSocket连接URL"""
        token = self.tokens.get(agent_id)
        if token:
            return f"ws://192.168.1.203:8004/mcp_endpoint/call/?token={token}"
        return None
    
    def get_sse_url(self, agent_id: str) -> Optional[str]:
        """获取SSE连接URL"""
        token = self.tokens.get(agent_id)
        if token:
            return f"http://192.168.1.203:8004/mcp_endpoint/sse/{agent_id}?token={token}"
        return None
    
    def list_agents(self) -> List[str]:
        """列出所有已生成token的agent_id"""
        return list(self.tokens.keys())
    
    def remove_agent(self, agent_id: str) -> bool:
        """移除指定agent_id的token"""
        if agent_id in self.tokens:
            del self.tokens[agent_id]
            logger.info(f"✅ 已移除 {agent_id} 的token")
            return True
        return False

async def main():
    """主函数 - 演示如何使用TokenManager"""
    manager = TokenManager()
    
    # 生成多个agent_id的token
    agent_ids = [
        "agent_001",
        "agent_002", 
        "agent_003",
        "3ec0027f77724376b50a9842ed39fd79"
    ]
    
    logger.info("=== 开始生成多个agent_id的token ===")
    
    for agent_id in agent_ids:
        token = await manager.generate_token(agent_id)
        if token:
            logger.info(f"Agent ID: {agent_id}")
            logger.info(f"Token: {token}")
            logger.info(f"WebSocket URL: {manager.get_websocket_url(agent_id)}")
            logger.info(f"SSE URL: {manager.get_sse_url(agent_id)}")
            logger.info("-" * 50)
    
    logger.info(f"✅ 总共为 {len(manager.list_agents())} 个agent生成了token")
    
    # 演示获取已存在的token
    logger.info("=== 测试获取已存在的token ===")
    existing_token = await manager.get_token("agent_001")
    if existing_token:
        logger.info(f"✅ 成功获取agent_001的token: {existing_token[:50]}...")

if __name__ == "__main__":
    asyncio.run(main())
