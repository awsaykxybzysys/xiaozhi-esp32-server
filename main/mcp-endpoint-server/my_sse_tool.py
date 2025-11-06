#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的SSE工具示例
"""

import asyncio
import aiohttp
import json
import logging
import time
import websockets

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MySSETool')

class MySSETool:
    """我的SSE工具"""
    
    def __init__(self):
        self.endpoint_url = "http://192.168.6.237:8004"  # 使用与Web端一致的服务器地址
        self.agent_id = "3538bde8a5504f3a8a504c161fdba08d"  # 使用与token中一致的agent_id
        self.token = "zDKP4DFRnbfUihY2h1E8838k3L1uP6ECqB87D/ssakZWYyplcgG4bNzMJh2IUuXz"  # 使用与Web端一致的token
        self.sse_id = None
        
    async def start(self):
        """启动SSE工具"""
        logger.info("=== 启动我的SSE工具 ===")
        
        # 使用WebSocket连接，像stdio模式一样
        
        # 构建WebSocket URL
        ws_url = f"ws://{self.endpoint_url.replace('http://', '')}/mcp_endpoint/mcp/?token={self.token}"
        logger.info(f"连接到WebSocket端点: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info("WebSocket连接已建立")
                
                # 处理消息
                while True:
                    try:
                        message = await websocket.recv()
                        await self._handle_websocket_message(message, websocket)
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("WebSocket连接已关闭")
                        break
                    except Exception as e:
                        logger.error(f"处理WebSocket消息时发生错误: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"WebSocket连接失败: {e}")
                            
    async def _handle_websocket_message(self, message, websocket):
        """处理WebSocket消息"""
        try:
            # 解析JSON-RPC消息
            data = json.loads(message)
            method = data.get('method')
            params = data.get('params', {})
            request_id = data.get('id')
            
            logger.info(f"收到MCP请求: {method}")
            
            if method == 'initialize':
                # 处理初始化请求
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "my-sse-tool",
                            "version": "1.0.0"
                        }
                    }
                }
                await websocket.send(json.dumps(response))
                logger.info(f"✅ 初始化响应已发送: {method}")
                
            elif method == 'tools/list':
                # 处理工具列表请求
                tools = [
                    {
                        "name": "my_calculator",
                        "description": "执行基本数学计算",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "expression": {
                                    "type": "string",
                                    "description": "要计算的数学表达式，如 '2 + 3 * 4'"
                                }
                            },
                            "required": ["expression"]
                        }
                    }
                ]
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": tools
                    }
                }
                await websocket.send(json.dumps(response))
                logger.info(f"✅ 工具列表响应已发送: {method}")
                
            elif method == 'tools/call':
                # 处理工具调用请求
                tool_name = params.get('name')
                tool_args = params.get('arguments', {})
                
                if tool_name == 'my_calculator':
                    result = await self._handle_calculator(tool_args)
                else:
                    result = {"error": f"未知工具: {tool_name}"}
                    
                # 发送响应
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False)
                            }
                        ]
                    }
                }
                
                await websocket.send(json.dumps(response))
                logger.info(f"✅ 工具调用响应已发送: {tool_name}")
                
        except json.JSONDecodeError as e:
            logger.error(f"解析WebSocket消息失败: {e}")
        except Exception as e:
            logger.error(f"处理WebSocket消息时发生错误: {e}")
            
        
            
    async def _handle_calculator(self, args):
        """处理计算器工具调用"""
        expression = args.get('expression', '')
        try:
            result = eval(expression)
            return {
                "expression": expression,
                "result": result,
                "status": "success"
            }
        except Exception as e:
            return {
                "expression": expression,
                "error": str(e),
                "status": "error"
            }
            

async def main():
    """主函数"""
    tool = MySSETool()
    
    try:
        await tool.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止...")
    except Exception as e:
        logger.error(f"工具运行出错: {e}")

if __name__ == "__main__":
    asyncio.run(main())
