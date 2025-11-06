#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试token解密
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.utils.aes_utils import decrypt
from src.utils.config import config
import json

def test_token_decrypt():
    """测试token解密"""
    # 原始token
    token = "2ZberFvI+/65Rk3BMmfctyfW8dNHZPvaP9r7gRxEDRM="
    
    print(f"测试token: {token}")
    
    # 获取配置的key
    key = config.get("server", "key", "")
    print(f"配置的key: {key}")
    
    # 尝试解密
    try:
        decrypted_data = decrypt(key, token)
        print(f"解密结果: {decrypted_data}")
        
        if decrypted_data:
            # 尝试解析JSON
            try:
                data = json.loads(decrypted_data)
                print(f"解析的JSON: {data}")
                agent_id = data.get("agentId")
                print(f"agentId: {agent_id}")
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
        else:
            print("解密失败")
            
    except Exception as e:
        print(f"解密过程出错: {e}")

if __name__ == "__main__":
    test_token_decrypt()





