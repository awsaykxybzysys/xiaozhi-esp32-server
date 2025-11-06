# 多Agent ID支持指南

## 概述

现在MCP Endpoint Server支持多个Agent ID，不再局限于硬编码的`single_module`。每个Agent ID都可以有独立的token和连接。

## 新增功能

### 1. 动态Token生成API

**端点**: `GET /mcp_endpoint/token/{agent_id}`

**功能**: 为指定的agent_id生成token

**示例**:
```bash
curl "http://192.168.1.203:8004/mcp_endpoint/token/agent_001"
```

**响应**:
```json
{
  "result": {
    "agent_id": "agent_001",
    "token": "encrypted_token_here",
    "websocket_url": "ws://192.168.1.203:8004/mcp_endpoint/call/?token=...",
    "sse_url": "http://192.168.1.203:8004/mcp_endpoint/sse/agent_001?token=..."
  }
}
```

### 2. Token管理器

**文件**: `token_manager.py`

**功能**: 管理多个agent_id的token生成和存储

**使用示例**:
```python
from token_manager import TokenManager

manager = TokenManager()
token = await manager.generate_token("agent_001")
websocket_url = manager.get_websocket_url("agent_001")
sse_url = manager.get_sse_url("agent_001")
```

### 3. 动态SSE工具

**文件**: `dynamic_sse_tool.py`

**功能**: 支持任意agent_id的SSE工具

**使用示例**:
```bash
python dynamic_sse_tool.py agent_001
python dynamic_sse_tool.py agent_002
```

## 使用方法

### 方法1: 使用Token管理器

1. **生成Token**:
```python
from token_manager import TokenManager

manager = TokenManager()
token = await manager.generate_token("your_agent_id")
```

2. **创建SSE工具**:
```python
from dynamic_sse_tool import DynamicSSETool

tool = DynamicSSETool("your_agent_id")
await tool.start()
```

3. **测试连接**:
```python
# 使用生成的token进行WebSocket连接测试
websocket_url = manager.get_websocket_url("your_agent_id")
```

### 方法2: 直接使用API

1. **获取Token**:
```bash
curl "http://192.168.1.203:8004/mcp_endpoint/token/your_agent_id"
```

2. **使用Token连接**:
```bash
# WebSocket连接
ws://192.168.1.203:8004/mcp_endpoint/call/?token=your_token

# SSE连接
http://192.168.1.203:8004/mcp_endpoint/sse/your_agent_id?token=your_token
```

## 测试脚本

### 1. 测试Token生成
```bash
python token_manager.py
```

### 2. 测试多个Agent
```bash
python test_multiple_agents.py
```

### 3. 测试单个动态SSE工具
```bash
python dynamic_sse_tool.py agent_001
```

## 架构说明

### 认证流程
1. 客户端请求指定agent_id的token
2. 服务器生成包含该agent_id的加密token
3. 客户端使用token连接WebSocket或SSE端点
4. 服务器验证token并提取agent_id
5. 验证URL路径中的agent_id与token中的agent_id是否匹配

### 连接管理
- 每个agent_id可以有独立的WebSocket连接
- 每个agent_id可以有独立的SSE连接
- 连接管理器按agent_id分组管理连接

### 工具注册
- 每个agent_id可以注册独立的工具集
- 工具名称可以包含agent_id以避免冲突
- 支持动态工具注册和注销

## 最佳实践

### 1. Agent ID命名
- 使用有意义的名称，如`user_001`、`device_001`
- 避免使用特殊字符
- 保持唯一性

### 2. Token管理
- 定期轮换token
- 安全存储token
- 不要泄露token给未授权用户

### 3. 工具命名
- 在工具名称中包含agent_id
- 使用描述性的工具名称
- 避免工具名称冲突

### 4. 错误处理
- 处理token过期情况
- 处理连接断开情况
- 实现重连机制

## 示例场景

### 场景1: 多用户系统
```python
# 为不同用户创建独立的agent
user_agents = ["user_001", "user_002", "user_003"]

for user_id in user_agents:
    token = await manager.generate_token(user_id)
    # 启动该用户的SSE工具
    tool = DynamicSSETool(user_id)
    await tool.start()
```

### 场景2: 多设备管理
```python
# 为不同设备创建独立的agent
device_agents = ["device_001", "device_002", "device_003"]

for device_id in device_agents:
    token = await manager.generate_token(device_id)
    # 启动该设备的SSE工具
    tool = DynamicSSETool(device_id)
    await tool.start()
```

### 场景3: 多租户系统
```python
# 为不同租户创建独立的agent
tenant_agents = ["tenant_a", "tenant_b", "tenant_c"]

for tenant_id in tenant_agents:
    token = await manager.generate_token(tenant_id)
    # 启动该租户的SSE工具
    tool = DynamicSSETool(tenant_id)
    await tool.start()
```

## 注意事项

1. **服务器重启**: 修改硬编码agent_id后需要重启服务器
2. **Token有效期**: 当前token没有过期机制，需要手动管理
3. **连接限制**: 每个agent_id的连接数限制需要根据实际需求调整
4. **安全性**: 生产环境中应该添加额外的权限验证机制

## 故障排除

### 问题1: Token生成失败
- 检查服务器是否运行
- 检查网络连接
- 检查agent_id格式

### 问题2: 认证失败
- 检查token是否正确
- 检查agent_id是否匹配
- 检查URL编码

### 问题3: 连接失败
- 检查防火墙设置
- 检查端口是否开放
- 检查服务器日志

## 更新日志

- **v1.0**: 支持硬编码的single_module
- **v2.0**: 支持动态agent_id和token生成
- **v2.1**: 添加Token管理器和动态SSE工具
- **v2.2**: 完善多Agent测试和文档
