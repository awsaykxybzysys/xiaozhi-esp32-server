#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSE功能测试脚本
"""

import asyncio
import aiohttp
import json
import time
import logging
from urllib.parse import quote

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SSETest')

class SSETester:
    """SSE功能测试器"""
    
    def __init__(self, endpoint_url: str = "http://localhost:8004"):
        self.endpoint_url = endpoint_url
        self.session = None
        
    async def test_sse_connection(self, agent_id: str, token: str):
        """测试SSE连接"""
        try:
            self.session = aiohttp.ClientSession()
            
            # 构建SSE URL
            sse_url = f"{self.endpoint_url}/mcp_endpoint/sse/{agent_id}?token={token}"
            logger.info(f"测试SSE连接: {sse_url}")
            
            # 建立SSE连接
            async with self.session.get(sse_url) as response:
                if response.status != 200:
                    logger.error(f"SSE连接失败: {response.status}")
                    return False
                
                logger.info("SSE连接已建立")
                
                # 读取前几条消息
                message_count = 0
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]  # 移除 'data: ' 前缀
                        try:
                            message = json.loads(data)
                            logger.info(f"收到SSE消息: {message}")
                            message_count += 1
                            
                            if message_count >= 3:  # 读取3条消息后停止
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"解析SSE消息失败: {e}")
                            
        except Exception as e:
            logger.error(f"SSE连接测试错误: {e}")
            return False
        finally:
            if self.session:
                await self.session.close()
                
        return True
    
    async def test_health_check(self):
        """测试健康检查"""
        try:
            async with aiohttp.ClientSession() as session:
                health_url = f"{self.endpoint_url}/mcp_endpoint/health?key=your_key_here"
                async with session.get(health_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"健康检查成功: {data}")
                        return True
                    else:
                        logger.error(f"健康检查失败: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"健康检查错误: {e}")
            return False

async def main():
    """主函数"""
    tester = SSETester()
    
    # 测试健康检查
    logger.info("=== 测试健康检查 ===")
    await tester.test_health_check()
    
    # 测试SSE连接（需要有效的token）
    logger.info("=== 测试SSE连接 ===")
    agent_id = "test_agent"
    token = "your_token_here"  # 需要替换为实际的token
    
    # 注意：这个测试需要有效的token才能成功
    # await tester.test_sse_connection(agent_id, token)

if __name__ == "__main__":
    asyncio.run(main())





