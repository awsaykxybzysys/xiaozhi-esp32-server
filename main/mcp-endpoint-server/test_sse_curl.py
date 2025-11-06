#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用requests测试SSE连接
"""

import requests
import json
import time

def test_sse_with_requests():
    """使用requests测试SSE连接"""
    endpoint_url = "http://192.168.6.237:8004"
    agent_id = "test_sse_agent"
    token = "2ZberFvI%2B/65Rk3BMmfctyfW8dNHZPvaP9r7gRxEDRM%3D"
    
    sse_url = f"{endpoint_url}/mcp_endpoint/sse/{agent_id}?token={token}"
    
    print(f"连接到SSE端点: {sse_url}")
    
    try:
        # 使用stream=True来接收SSE流
        response = requests.get(sse_url, stream=True, timeout=35)
        
        if response.status_code != 200:
            print(f"SSE连接失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
        
        print("SSE连接已建立")
        print("开始接收消息...")
        
        message_count = 0
        start_time = time.time()
        
        for line in response.iter_lines(decode_unicode=True):
            if time.time() - start_time > 30:  # 30秒超时
                print("等待超时，停止接收消息")
                break
                
            if line:
                print(f"收到原始行: {line}")
                
                if line.startswith('data: '):
                    data = line[6:]  # 移除 'data: ' 前缀
                    try:
                        message = json.loads(data)
                        message_count += 1
                        message_type = message.get("type", "unknown")
                        print(f"收到SSE消息 #{message_count} (类型: {message_type}): {message}")
                        
                        if message_type == "connected":
                            sse_id = message.get("sse_id")
                            print(f"✅ 连接确认，SSE ID: {sse_id}")
                        elif message_type == "heartbeat":
                            print("💓 收到心跳消息")
                        
                        # 收到连接确认和心跳后停止
                        if message_count >= 3:
                            print("已收到足够消息，停止接收")
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"解析SSE消息失败: {e}")
                        print(f"原始数据: {data}")
        
        print(f"总共收到 {message_count} 条SSE消息")
        return message_count > 0
        
    except requests.exceptions.Timeout:
        print("请求超时")
        return False
    except Exception as e:
        print(f"SSE连接测试错误: {e}")
        return False

if __name__ == "__main__":
    print("=== 开始SSE连接测试 (使用requests) ===")
    success = test_sse_with_requests()
    
    if success:
        print("✅ SSE连接测试成功！")
    else:
        print("❌ SSE连接测试失败！")





