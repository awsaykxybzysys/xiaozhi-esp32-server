#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试连接管理器
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import asyncio
from src.core.connection_manager import connection_manager

async def test_connection_manager():
    """测试连接管理器"""
    print("=== 测试连接管理器 ===")
    
    # 测试SSE连接注册
    print("1. 测试SSE连接注册")
    sse_id = await connection_manager.register_sse_connection("test_agent")
    print(f"SSE连接已注册: {sse_id}")
    
    # 测试SSE工具连接注册
    print("2. 测试SSE工具连接注册")
    await connection_manager.register_sse_tool_connection("test_agent", sse_id)
    print("SSE工具连接已注册")
    
    # 测试连接状态
    print("3. 测试连接状态")
    print(f"is_tool_connected: {connection_manager.is_tool_connected('test_agent')}")
    print(f"is_sse_connected: {connection_manager.is_sse_connected(sse_id)}")
    
    # 测试连接统计
    print("4. 测试连接统计")
    stats = connection_manager.get_connection_stats()
    print(f"连接统计: {stats}")
    
    # 清理
    print("5. 清理连接")
    await connection_manager.unregister_sse_connection(sse_id)
    await connection_manager.unregister_sse_tool_connection("test_agent")
    print("连接已清理")

if __name__ == "__main__":
    asyncio.run(test_connection_manager())





