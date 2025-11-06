#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的SSE测试工具
"""

import asyncio
import aiohttp
import json
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SimpleSSETest')

async def test_sse_connection():
    """测试SSE连接"""
    endpoint_url = "http://192.168.6.237:8004"
    agent_id = "single_module"  # 使用token中解密出来的正确agent_id
    token = "2ZberFvI%2B/65Rk3BMmfctyfW8dNHZPvaP9r7gRxEDRM%3D"  # 从服务器输出中获取的token
    
    try:
        async with aiohttp.ClientSession() as session:
            # 构建SSE URL
            sse_url = f"{endpoint_url}/mcp_endpoint/sse/{agent_id}?token={token}"
            logger.info(f"连接到SSE端点: {sse_url}")
            
            # 建立SSE连接
            async with session.get(sse_url) as response:
                if response.status != 200:
                    logger.error(f"SSE连接失败: {response.status}")
                    return False
                
                logger.info("SSE连接已建立")
                
                # 读取消息
                message_count = 0
                sse_id = None
                start_time = time.time()
                timeout = 35  # 等待35秒，确保能收到心跳消息
                
                async for line in response.content:
                    # 检查超时
                    if time.time() - start_time > timeout:
                        logger.info("等待超时，停止接收消息")
                        break
                    
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]  # 移除 'data: ' 前缀
                        try:
                            message = json.loads(data)
                            message_count += 1
                            
                            message_type = message.get("type", "unknown")
                            logger.info(f"收到SSE消息 #{message_count} (类型: {message_type}): {message}")
                            
                            # 获取SSE ID
                            if message_type == "connected":
                                sse_id = message.get("sse_id")
                                logger.info(f"✅ 连接确认，SSE ID: {sse_id}")
                            elif message_type == "heartbeat":
                                logger.info("💓 收到心跳消息")
                            
                            # 收到连接确认和心跳后停止
                            if message_count >= 3:
                                logger.info("已收到足够消息，停止接收")
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"解析SSE消息失败: {e}")
                
                logger.info(f"总共收到 {message_count} 条SSE消息")
                return True
                
    except Exception as e:
        logger.error(f"SSE连接测试错误: {e}")
        return False

async def main():
    """主函数"""
    logger.info("=== 开始SSE连接测试 ===")
    success = await test_sse_connection()
    
    if success:
        logger.info("✅ SSE连接测试成功！")
    else:
        logger.error("❌ SSE连接测试失败！")

if __name__ == "__main__":
    asyncio.run(main())
