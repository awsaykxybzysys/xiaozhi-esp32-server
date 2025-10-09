# 流式故事播放工具使用指南

## 概述

`stream_story_player` 是一个流式故事播放工具，可以实时播放各种类型的故事内容。它使用与 `stream_data_query` 相同的流式输出机制，支持实时语音播放。

## 功能特点

- **流式播放**：实时接收和播放故事片段
- **多种故事类型**：支持童话、寓言、小说、神话等
- **灵活主题**：支持冒险、爱情、友谊、成长等主题
- **可调长度**：支持短篇、中篇、长篇故事
- **实时语音**：每个故事片段都会立即播放语音
- **配置化**：通过配置文件管理API设置

## 配置

在 `config.yaml` 中添加以下配置：

```yaml
plugins:
  stream_story_player:
    api_url: "http://localhost:8008"  # 故事服务地址
    api_key: "123456789"  # API密钥
    timeout: 120  # 超时时间（秒），故事可能比较长
    default_story_types: ["童话", "寓言", "小说", "神话"]  # 默认支持的故事类型
    default_themes: ["冒险", "爱情", "友谊", "成长", "勇气"]  # 默认支持的主题
    default_lengths: ["短篇", "中篇", "长篇"]  # 默认支持的长度
```

## 使用方法

### 基本用法

```
播放一个童话故事
```

### 指定故事类型

```
播放一个寓言故事
```

### 指定主题

```
播放一个关于友谊的童话故事
```

### 指定长度

```
播放一个短篇冒险小说
```

### 完整参数

```
播放一个中篇的关于成长的童话故事
```

## 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| story_type | string | 是 | 故事类型：童话、寓言、小说、神话等 |
| story_theme | string | 否 | 故事主题：冒险、爱情、友谊、成长、勇气等 |
| story_length | string | 否 | 故事长度：短篇、中篇、长篇 |
| timeout | integer | 否 | 超时时间（秒），默认120秒 |

## 工作流程

1. **接收请求**：用户请求播放故事
2. **构建API请求**：根据参数构建故事API请求
3. **流式接收**：实时接收故事片段
4. **实时播放**：每个片段立即播放语音
5. **完成播放**：故事播放完成

## 技术实现

### 工具类型
- **ToolType**: `STREAM_OUTPUT` (18)
- **Action**: `STREAM_RESPONSE` (4)

### 流式处理
- 使用 `stream_callback` 函数处理每个故事片段
- 每个片段都会触发TTS播放
- 支持SSE格式的数据流

### 错误处理
- 网络超时处理
- API错误处理
- 数据解析错误处理

## 示例日志

```
250925 17:50:00[0.7.6-00000000000000][plugins_func.functions.stream_story_player]-INFO-开始播放故事: 请播放一个短篇的童话故事，主题是冒险, API: http://localhost:8008/api/story?key=123456789
250925 17:50:01[0.7.6-00000000000000][core.providers.tools.server_plugins.plugin_executor]-INFO-stream_callback被调用，数据: {'message': '从前有一个勇敢的小女孩...', 'story_type': '童话', 'fragment_number': 1}
250925 17:50:01[0.7.6-00000000000000][core.providers.tools.server_plugins.plugin_executor]-INFO-播放流式数据语音: 从前有一个勇敢的小女孩...
250925 17:50:02[0.7.6-00000000000000][core.providers.tools.server_plugins.plugin_executor]-INFO-stream_callback被调用，数据: {'message': '她决定踏上寻找宝藏的旅程...', 'story_type': '童话', 'fragment_number': 2}
250925 17:50:02[0.7.6-00000000000000][core.providers.tools.server_plugins.plugin_executor]-INFO-播放流式数据语音: 她决定踏上寻找宝藏的旅程...
...
250925 17:50:30[0.7.6-00000000000000][plugins_func.functions.stream_story_player]-INFO-故事播放完成，共处理 15 个片段
```

## 注意事项

1. **API兼容性**：确保故事API支持SSE格式的流式输出
2. **超时设置**：故事可能比较长，建议设置较长的超时时间
3. **语音播放**：每个故事片段都会立即播放，确保TTS服务正常
4. **网络稳定**：流式播放需要稳定的网络连接

## 扩展功能

可以根据需要扩展以下功能：

1. **故事收藏**：保存用户喜欢的故事
2. **播放历史**：记录播放过的故事
3. **个性化推荐**：根据用户喜好推荐故事
4. **多语言支持**：支持不同语言的故事
5. **背景音乐**：为故事添加背景音乐

