# MCP Endpoint Server SSE 支持

本文档介绍如何在MCP Endpoint Server中使用SSE（Server-Sent Events）模式注册第三方工具。

## 功能概述

MCP Endpoint Server现在支持三种工具连接模式：
1. **WebSocket模式** - 传统的WebSocket连接
2. **stdio模式** - 通过mcp_pipe.py桥接的stdio连接
3. **SSE模式** - 新增的Server-Sent Events连接

## SSE模式架构

```
第三方SSE工具 → mcp-endpoint-server SSE端点 → WebSocket转换 → xiaozhi-server
```

## 使用方法

### 1. 启动MCP Endpoint Server

```bash
cd mcp-endpoint-server
python main.py
```

### 2. 获取连接信息

启动后，服务器会输出连接信息：

```
智控台MCP参数配置: http://localhost:8004/mcp_endpoint/health?key=your_key
单模块部署MCP接入点: ws://localhost:8004/mcp_endpoint/mcp/?token=your_token
```

### 3. 创建SSE工具

#### 3.1 连接到SSE端点

```python
import asyncio
import aiohttp
import json

async def connect_sse_tool():
    endpoint_url = "http://localhost:8004"
    agent_id = "your_agent_id"
    token = "your_token"
    
    sse_url = f"{endpoint_url}/mcp_endpoint/sse/{agent_id}?token={token}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(sse_url) as response:
            async for line in response.content:
                if line.startswith(b'data: '):
                    data = line[6:].decode('utf-8')
                    message = json.loads(data)
                    print(f"收到消息: {message}")
```

#### 3.2 处理MCP请求

```python
async def handle_mcp_request(message):
    if message.get("type") == "mcp_request":
        mcp_message = message.get("mcp_message", {})
        method = mcp_message.get("method", "")
        
        if method == "tools/list":
            # 返回工具列表
            response = {
                "jsonrpc": "2.0",
                "id": mcp_message.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "my_tool",
                            "description": "我的工具",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "input": {"type": "string"}
                                }
                            }
                        }
                    ]
                }
            }
            
            # 发送响应
            await send_mcp_response(response)

async def send_mcp_response(response):
    message_data = {
        "type": "mcp_response",
        "sse_id": sse_id,  # 从连接确认消息中获取
        "mcp_message": response
    }
    
    message_url = f"{endpoint_url}/mcp_endpoint/sse/{agent_id}/message?token={token}"
    async with session.post(message_url, json=message_data) as resp:
        print(f"响应发送状态: {resp.status}")
```

### 4. 配置xiaozhi-server

在xiaozhi-server的配置中，SSE工具会自动通过mcp-endpoint-server被发现，无需额外配置。

## API端点

### SSE端点

- **GET** `/mcp_endpoint/sse/{agent_id}?token={token}`
  - 建立SSE连接
  - 接收MCP请求和心跳消息

### 消息端点

- **POST** `/mcp_endpoint/sse/{agent_id}/message?token={token}`
  - 发送MCP响应消息
  - 请求体格式：
    ```json
    {
        "type": "mcp_response",
        "sse_id": "sse_connection_id",
        "mcp_message": {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {...}
        }
    }
    ```

## 消息格式

### SSE消息格式

```json
{
    "type": "connected|mcp_request|heartbeat",
    "agent_id": "agent_id",
    "sse_id": "sse_connection_id",
    "mcp_message": {...},  // 仅mcp_request类型包含
    "timestamp": 1234567890
}
```

### 工具响应格式

```json
{
    "type": "mcp_response",
    "sse_id": "sse_connection_id",
    "mcp_message": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "工具执行结果"
                }
            ]
        }
    }
}
```

## 示例工具

参考 `example_sse_tool.py` 文件，这是一个完整的SSE工具示例，包含：
- SSE连接建立
- MCP请求处理
- 工具列表返回
- 工具调用处理

## 测试

运行测试脚本：

```bash
python test_sse.py
```

## 注意事项

1. **认证**: 所有SSE连接都需要有效的token
2. **心跳**: SSE连接会定期发送心跳消息保持连接
3. **错误处理**: 连接断开时会自动清理资源
4. **并发**: 支持多个SSE工具同时连接
5. **兼容性**: SSE工具与WebSocket工具完全兼容

## 故障排除

### 连接失败
- 检查token是否正确
- 确认agent_id是否匹配
- 查看服务器日志

### 消息发送失败
- 确认sse_id是否正确
- 检查消息格式是否符合要求
- 验证连接是否仍然活跃

### 工具未发现
- 确认工具已正确实现tools/list方法
- 检查xiaozhi-server是否正确连接到mcp-endpoint-server
- 查看连接统计信息





