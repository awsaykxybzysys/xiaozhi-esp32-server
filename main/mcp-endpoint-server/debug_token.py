#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试token问题
"""

import requests
from urllib.parse import quote, unquote

def test_token():
    """测试token"""
    # 原始token
    original_token = "2ZberFvI%2B/65Rk3BMmfctyfW8dNHZPvaP9r7gRxEDRM%3D"
    
    print(f"原始token: {original_token}")
    
    # URL解码
    decoded_token = unquote(original_token)
    print(f"解码后token: {decoded_token}")
    
    # 重新URL编码
    reencoded_token = quote(decoded_token)
    print(f"重新编码token: {reencoded_token}")
    
    # 测试不同的token格式
    tokens_to_test = [
        original_token,
        decoded_token,
        reencoded_token
    ]
    
    endpoint_url = "http://192.168.6.237:8004"
    agent_id = "test_sse_agent"
    
    for i, token in enumerate(tokens_to_test):
        print(f"\n=== 测试token {i+1}: {token} ===")
        
        # 测试健康检查
        health_url = f"{endpoint_url}/mcp_endpoint/health?key=0eeaf16f74884a7a8e4ef1cdfad821e5"
        try:
            response = requests.get(health_url)
            print(f"健康检查状态: {response.status_code}")
            if response.status_code == 200:
                print(f"健康检查响应: {response.json()}")
        except Exception as e:
            print(f"健康检查错误: {e}")
        
        # 测试SSE端点
        sse_url = f"{endpoint_url}/mcp_endpoint/sse/{agent_id}?token={token}"
        try:
            response = requests.get(sse_url, timeout=5)
            print(f"SSE端点状态: {response.status_code}")
            print(f"SSE端点响应: {response.text[:200]}...")
        except Exception as e:
            print(f"SSE端点错误: {e}")

if __name__ == "__main__":
    test_token()

