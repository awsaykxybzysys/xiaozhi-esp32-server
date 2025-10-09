# AI Agent数据查询助手

## 📋 功能说明

这是一个简单的AI Agent流式交互数据查询工具，用于查询ESP32 AI Agent的状态、对话历史和统计信息。

## 🔧 配置方法

### 1. 在config.yaml中添加配置

```yaml
plugins:
  ai_agent_data:
    api_host: "localhost:8000"      # AI Agent服务器地址
    api_key: "your_api_key"         # API密钥（可选）
    default_limit: 10               # 默认查询限制
    cache_ttl: 300                  # 缓存时间（秒）
    enable_cache: true              # 是否启用缓存
    timeout: 10                     # 超时时间（秒）
```

### 2. 重启服务

```bash
python app.py
```

## 🚀 使用方法

### 查询AI Agent状态
```
查询AI Agent状态
```

### 查询对话历史
```
查看对话历史
```

### 查询统计信息
```
查看AI Agent统计
```

## 📊 返回数据格式

### 状态信息
- 状态: 运行中/停止
- 处理中: true/false
- 当前对话ID
- 总对话数
- 活跃连接数
- 内存使用
- 运行时间
- API状态
- 响应模式

### 对话历史
- 对话ID
- 查询内容
- 响应内容
- 时间
- 用户ID

### 统计信息
- 总对话数
- 总查询数
- 平均响应时间
- 成功率
- 今日/本周/本月对话数
- 常见查询类型

## 🔍 工具特点

- **简单易用**: 只需一个参数即可查询
- **配置灵活**: 支持从配置文件读取API信息
- **缓存支持**: 可配置缓存时间提高性能
- **错误处理**: 完善的错误处理机制
- **日志记录**: 详细的操作日志

## 📝 代码示例

```python
# 工具注册
@register_function("ai_agent_data", AI_AGENT_DATA_DESC, ToolType.WAIT)
def ai_agent_data(conn, query_type: str):
    # 从配置获取API信息
    api_host = conn.config["plugins"]["ai_agent_data"].get("api_host", "localhost:8000")
    api_key = conn.config["plugins"]["ai_agent_data"].get("api_key", "default_key")
    
    # 根据查询类型返回相应数据
    if query_type == "status":
        # 返回状态信息
    elif query_type == "history":
        # 返回历史记录
    elif query_type == "stats":
        # 返回统计信息
```

## 🎯 适用场景

- 监控AI Agent运行状态
- 查看用户交互历史
- 分析系统使用统计
- 故障排查和调试
- 性能监控

## ⚙️ 扩展功能

可以根据需要扩展更多功能：
- 实时数据推送
- 数据导出
- 告警通知
- 性能分析
- 用户行为分析



