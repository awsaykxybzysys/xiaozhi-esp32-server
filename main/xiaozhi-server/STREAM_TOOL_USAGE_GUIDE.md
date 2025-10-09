# 流式工具使用指南

## 概述

新增的 `STREAM_OUTPUT` 工具类型支持流式数据输出，可以实时接收和推送数据片段，适用于实时数据监控、流式文本生成等场景。

## 核心特性

- **实时流式输出**：支持HTTP API的流式数据接收
- **多种数据格式**：支持JSON、文本、二进制等多种数据格式
- **超时控制**：支持自定义超时时间，防止长时间阻塞
- **错误处理**：完善的异常处理和错误恢复机制
- **标准格式**：统一的数据片段格式，便于前端处理

## 工具类型定义

### ToolType.STREAM_OUTPUT (18)
```python
STREAM_OUTPUT = (18, "调用工具后，持续等待工具的流式输出")
```

### Action.STREAM_RESPONSE (4)
```python
STREAM_RESPONSE = (4, "流式响应，持续输出数据片段")
```

## 数据格式规范

### 流式数据片段格式
```python
{
    'content': [{
        'type': 'text',
        'data': '{"success": true, "result": "api请求的结果"}'
    }],
    'isError': False
}
```

### 结束信号格式
```python
{
    "message": "DONE",
    "timestamp": 1758787669,
    "total_messages": 20
}
```

## 使用方法

### 1. 注册流式工具

```python
from plugins_func.register import register_function, ToolType, ActionResponse, Action

@register_function("my_stream_tool", FUNCTION_DESC, ToolType.STREAM_OUTPUT)
async def my_stream_tool(conn, param1: str, stream_callback=None):
    """流式工具函数"""
    try:
        # 从配置获取API信息
        api_url = conn.config["plugins"]["my_stream_tool"].get(
            "api_url", "http://localhost:8080/api/stream"
        )
        api_key = conn.config["plugins"]["my_stream_tool"].get(
            "api_key", ""
        )
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # 调用HTTP API获取流式数据
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json={"param": param1}, headers=headers) as response:
                async for line in response.content:
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        
                        # 检查结束信号
                        if data.get("message") == "DONE":
                            break
                            
                        # 发送数据片段
                        if stream_callback:
                            await stream_callback(data)
        
        return ActionResponse(Action.STREAM_RESPONSE, result="流式传输完成")
    except Exception as e:
        return ActionResponse(Action.ERROR, response=str(e))
```

### 2. 函数描述格式

```python
FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "my_stream_tool",
        "description": "流式数据查询工具的描述",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "参数描述"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认60秒"
                }
            },
            "required": ["param1"]
        }
    }
}
```

## 示例工具

### 1. stream_data_query
- **功能**：流式数据查询工具
- **参数**：query（查询内容）、api_url（API地址）、timeout（超时时间）
- **用途**：实时获取和推送数据流

### 2. stream_mock_data
- **功能**：模拟流式数据生成工具
- **参数**：count（数据片段数量）、interval（间隔时间）、data_type（数据类型）
- **用途**：测试流式输出功能

## 技术实现

### 1. 流式回调机制
- 系统自动创建 `stream_callback` 函数
- 每个数据片段通过回调函数实时发送
- 支持异步处理和错误恢复

### 2. 连接管理
- 自动管理HTTP连接的生命周期
- 支持连接超时和重试机制
- 优雅处理连接中断

### 3. 数据解析
- 支持SSE（Server-Sent Events）格式
- 自动解析JSON数据
- 处理多种数据编码格式

## 注意事项

1. **异步函数**：流式工具函数必须是 `async` 函数
2. **参数传递**：流式工具会自动传递 `conn` 和 `stream_callback` 参数
3. **错误处理**：必须妥善处理异常，返回适当的 `ActionResponse`
4. **资源清理**：确保HTTP连接和资源得到正确释放
5. **超时控制**：建议设置合理的超时时间，避免长时间阻塞

## 配置要求

### 配置文件设置
在 `config.yaml` 中添加流式工具的配置：

```yaml
plugins:
  stream_data_query:
    api_url: "https://your-api-endpoint.com/stream"
    api_key: "your-api-key-here"
    timeout: 60  # 可选，默认60秒
```

### 依赖库
```python
aiohttp>=3.8.0  # 异步HTTP客户端
asyncio         # 异步编程支持
json            # JSON数据处理
```

### 系统要求
- Python 3.7+
- 支持异步编程的Python环境
- 网络连接支持

## 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连接
   - 调整超时时间参数
   - 确认API服务可用性

2. **数据解析错误**
   - 检查API返回格式
   - 确认JSON格式正确性
   - 处理非标准数据格式

3. **流式传输中断**
   - 检查网络稳定性
   - 确认API支持流式输出
   - 查看错误日志信息

### 调试建议

1. 启用详细日志记录
2. 使用模拟工具测试功能
3. 检查网络连接状态
4. 验证API接口可用性
