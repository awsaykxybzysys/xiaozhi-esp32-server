# 网页抓取工具 (Web Scraper)

基于 `sse_server.py` 的网页抓取功能，集成到小智AI助手的插件系统中。

## 功能特性

- **多种内容提取模式**：支持纯文本、HTML源码、标题、链接、智能摘要等提取方式
- **智能缓存机制**：避免重复抓取，提高响应速度
- **错误处理**：完善的超时、重定向、错误状态处理
- **配置化**：支持通过配置文件自定义超时时间、内容长度等参数
- **异步支持**：提供异步和同步两种调用方式

## 安装依赖

确保已安装以下依赖包：

```bash
pip install httpx beautifulsoup4
```

这些依赖已在 `requirements.txt` 中列出。

## 配置说明

在 `config.yaml` 中添加以下配置：

```yaml
plugins:
  web_scraper:
    default_timeout: 10  # 默认超时时间（秒）
    default_max_length: 5000  # 默认最大内容长度
    cache_ttl: 1800  # 缓存时间（秒），30分钟
    user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
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

## 函数注册

网页抓取功能已自动注册到系统中，函数名称为：
- `web_scraper`: 异步版本
- `web_scraper_sync`: 同步版本

## 返回格式

函数返回 `ActionResponse` 对象，包含以下信息：

```
网页标题: [网页标题]

抓取URL: [实际抓取的URL]

内容类型: [提取类型]

==================================================

[提取的内容]
```

## 错误处理

- **网络错误**: 自动重试，超时处理
- **HTTP错误**: 返回状态码和错误信息
- **解析错误**: 返回友好的错误提示
- **缓存机制**: 避免重复请求，提高性能

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

### 抓取特定内容长度

```python
# 限制内容长度为1000字符
result = await web_scraper(
    conn, 
    "https://long-article.com", 
    "text", 
    max_length=1000
)
```

## 性能优化

1. **缓存机制**: 相同URL和参数的内容会被缓存30分钟
2. **异步处理**: 支持并发请求，提高效率
3. **智能解析**: 自动移除无关标签，提取核心内容
4. **超时控制**: 避免长时间等待，提高响应速度

## 注意事项

1. 请遵守网站的robots.txt和使用条款
2. 避免过于频繁的请求，以免被网站封禁
3. 某些网站可能有反爬虫机制，需要特殊处理
4. 建议设置合理的超时时间和内容长度限制

## 测试

运行测试脚本验证功能：

```bash
python simple_web_scraper_test.py
```

## 与原始sse_server.py的对比

| 特性 | sse_server.py | web_scraper.py |
|------|---------------|----------------|
| 集成方式 | 独立MCP服务器 | 插件系统集成 |
| 调用方式 | HTTP API | 函数调用 |
| 内容处理 | 原始HTML | 多种提取模式 |
| 缓存机制 | 无 | 智能缓存 |
| 错误处理 | 基础 | 完善 |
| 配置化 | 硬编码 | 配置文件 |

## 扩展功能

可以基于此工具进一步扩展：

1. **图片抓取**: 提取网页中的图片链接
2. **表格数据**: 解析HTML表格为结构化数据
3. **RSS解析**: 支持RSS/Atom订阅源
4. **PDF处理**: 集成PDF内容提取
5. **多语言支持**: 根据网页语言自动调整处理方式
