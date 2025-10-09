# 网页抓取工具 (Web Scraper) - SSE版本

基于 `sse_server.py` 的网页抓取功能，通过SSE服务器进行网页内容抓取。

## 功能特性

- **SSE服务器集成**：通过调用 `sse_server.py` 启动的SSE服务器来抓取网页
- **多种内容提取模式**：支持纯文本、HTML源码、标题、链接、智能摘要等提取方式
- **智能缓存机制**：避免重复抓取，提高响应速度
- **配置化**：支持通过配置文件自定义SSE服务器地址、超时时间等参数
- **域名验证**：支持域名白名单和黑名单验证

## 配置说明

### 1. 启动SSE服务器

首先需要启动 `sse_server.py`：

```bash
python sse_server.py
```

SSE服务器将在 `http://localhost:8008` 启动。

### 2. 配置小智系统

在 `config.yaml` 中添加以下配置：

```yaml
plugins:
  web_scraper:
    sse_server_url: "http://localhost:8008"  # SSE服务器地址
    default_timeout: 10  # 默认超时时间（秒）
    default_max_length: 5000  # 默认最大内容长度
    cache_ttl: 1800  # 缓存时间（秒），30分钟
    # 默认抓取的URL列表（当用户没有指定URL时使用）
    default_urls:
      - "https://www.baidu.com"
      - "https://www.example.com"
    # 允许的域名白名单（可选，为空表示允许所有域名）
    allowed_domains: []
    # 禁止的域名黑名单（可选）
    blocked_domains: []
```

## 使用方法

### 1. 基本用法

```python
# 抓取网页文本内容
result = await web_scraper(conn, "https://example.com", "text")

# 抓取网页标题
result = await web_scraper(conn, "https://example.com", "title")

# 抓取网页链接
result = await web_scraper(conn, "https://example.com", "links")
```

### 2. 参数说明

- `url` (必需): 要抓取的网页URL，支持http和https协议
- `extract_type` (可选): 提取内容类型
  - `"text"`: 纯文本内容（默认）
  - `"html"`: HTML源码
  - `"title"`: 仅标题
  - `"links"`: 仅链接
  - `"summary"`: 智能摘要
- `max_length` (可选): 返回内容的最大长度，默认5000字符
- `timeout` (可选): 请求超时时间（秒），默认10秒

### 3. 同步版本

如果需要在同步环境中使用，可以使用 `web_scraper_sync` 函数：

```python
result = web_scraper_sync(conn, "https://example.com", "text")
```

## 工作流程

1. **接收请求**：用户通过AI助手请求抓取网页
2. **配置获取**：从配置文件获取SSE服务器地址和其他参数
3. **域名验证**：检查目标URL是否在允许/禁止列表中
4. **缓存检查**：检查是否已有缓存结果
5. **SSE调用**：向SSE服务器发送抓取请求
6. **内容处理**：根据提取类型处理返回的HTML内容
7. **结果缓存**：将处理结果缓存起来
8. **返回结果**：返回格式化的抓取结果

## SSE服务器通信

### 请求格式

```json
{
  "name": "fetch",
  "arguments": {
    "url": "https://example.com"
  }
}
```

### 响应格式

```json
{
  "success": true,
  "result": "<html>...</html>",
  "timestamp": 1234567890.123
}
```

## 错误处理

- **SSE服务器连接失败**：检查SSE服务器是否启动
- **网络错误**：自动重试，超时处理
- **HTTP错误**：返回状态码和错误信息
- **域名验证失败**：返回域名限制信息
- **解析错误**：返回友好的错误提示

## 示例用法

### 抓取新闻网站内容

```python
# 抓取新闻摘要
result = await web_scraper(
    conn, 
    "https://news.example.com/article/123", 
    "summary", 
    max_length=2000
)
```

### 获取网页链接列表

```python
# 获取网页中的所有链接
result = await web_scraper(conn, "https://example.com", "links")
```

### 使用默认URL

```python
# 不提供URL，使用配置文件中的默认URL
result = await web_scraper(conn, None, "text")
```

## 性能优化

1. **缓存机制**：相同URL和参数的内容会被缓存30分钟
2. **异步处理**：支持并发请求，提高效率
3. **智能解析**：自动移除无关标签，提取核心内容
4. **超时控制**：避免长时间等待，提高响应速度

## 注意事项

1. 确保SSE服务器 (`sse_server.py`) 已启动并运行在配置的地址上
2. 请遵守网站的robots.txt和使用条款
3. 避免过于频繁的请求，以免被网站封禁
4. 某些网站可能有反爬虫机制，需要特殊处理
5. 建议设置合理的超时时间和内容长度限制

## 故障排查

### 1. SSE服务器连接失败

```
SSE服务器抓取失败: SSE服务器请求错误: Connection refused
```

**解决方案**：
- 检查SSE服务器是否启动：`python sse_server.py`
- 检查配置文件中的 `sse_server_url` 是否正确
- 检查防火墙设置

### 2. 域名验证失败

```
域名验证失败: 域名 example.com 在禁止列表中
```

**解决方案**：
- 检查配置文件中的 `blocked_domains` 设置
- 将域名添加到 `allowed_domains` 中（如果启用了白名单）

### 3. 超时错误

```
SSE服务器抓取失败: SSE服务器请求超时
```

**解决方案**：
- 增加配置文件中的 `default_timeout` 值
- 检查网络连接状况

## 与直接抓取的对比

| 特性 | 直接抓取 | SSE服务器抓取 |
|------|---------|---------------|
| 实现复杂度 | 简单 | 中等 |
| 服务器资源 | 高 | 低 |
| 扩展性 | 有限 | 高 |
| 错误处理 | 基础 | 完善 |
| 缓存机制 | 无 | 有 |
| 配置灵活性 | 低 | 高 |

## 扩展功能

可以基于此工具进一步扩展：

1. **多SSE服务器支持**：支持多个SSE服务器负载均衡
2. **代理支持**：通过SSE服务器配置代理
3. **用户认证**：支持需要认证的网站抓取
4. **内容过滤**：根据关键词过滤抓取内容
5. **定时抓取**：支持定时抓取指定网站
