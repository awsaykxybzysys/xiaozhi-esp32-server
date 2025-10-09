# 小智项目工具注册指南

## 📋 概述

小智项目支持多种类型的工具注册，包括：
- **服务端插件** (Server Plugin)
- **MCP工具** (MCP Tools) 
- **IoT设备控制** (IoT Control)
- **系统控制** (System Control)

## 🔧 工具注册方式

### 1. 服务端插件工具 (推荐)

这是最常用的工具注册方式，适合大多数功能工具。

#### 创建工具文件

在 `plugins_func/functions/` 目录下创建新的Python文件：

```python
# plugins_func/functions/my_tool.py
from plugins_func.register import register_function, ToolType, ActionResponse, Action

# 定义工具描述
my_tool_function_desc = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "我的工具描述，说明工具的功能和用途",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "参数1的描述"
                },
                "param2": {
                    "type": "integer", 
                    "description": "参数2的描述"
                }
            },
            "required": ["param1"]
        }
    }
}

@register_function("my_tool", my_tool_function_desc, ToolType.WAIT)
def my_tool(param1: str, param2: int = 10):
    """
    我的工具函数实现
    """
    try:
        # 工具逻辑实现
        result = f"处理参数: {param1}, {param2}"
        
        # 返回结果
        return ActionResponse(
            action=Action.REQLLM,  # 请求LLM生成回复
            result=result,
            response=None
        )
    except Exception as e:
        return ActionResponse(
            action=Action.ERROR,
            result=f"工具执行错误: {str(e)}",
            response=None
        )
```

#### 工具类型说明

- **`ToolType.WAIT`**: 等待函数返回，然后请求LLM生成回复
- **`ToolType.NONE`**: 调用完工具后，不做其他操作
- **`ToolType.SYSTEM_CTL`**: 系统控制，需要传递conn参数
- **`ToolType.IOT_CTL`**: IoT设备控制，需要传递conn参数
- **`ToolType.CHANGE_SYS_PROMPT`**: 修改系统提示词

#### 返回类型说明

- **`Action.REQLLM`**: 请求LLM生成回复
- **`Action.RESPONSE`**: 直接回复
- **`Action.ERROR`**: 错误处理
- **`Action.NOTFOUND`**: 未找到函数

### 2. MCP工具注册

#### 配置文件方式

在 `data/.mcp_server_settings.json` 中添加MCP服务器配置：

```json
{
  "mcpServers": {
    "MyMCPTool": {
      "url": "http://localhost:8000/sse",
      "env": {
        "API_KEY": "your_api_key"
      }
    }
  }
}
```

#### 代码方式

```python
# 在工具执行器中注册MCP工具
from core.providers.tools.server_mcp import ServerMCPExecutor

mcp_executor = ServerMCPExecutor(conn)
mcp_executor.register_tool("my_mcp_tool", {
    "name": "my_mcp_tool",
    "description": "MCP工具描述",
    "parameters": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "参数描述"}
        }
    }
})
```

### 3. IoT设备工具

```python
# plugins_func/functions/device_control.py
from plugins_func.register import register_function, ToolType, ActionResponse, Action

@register_function("control_device", device_control_desc, ToolType.IOT_CTL)
def control_device(conn, device_id: str, action: str):
    """
    IoT设备控制工具
    """
    try:
        # 设备控制逻辑
        result = f"设备 {device_id} 执行 {action}"
        
        return ActionResponse(
            action=Action.RESPONSE,
            result=result,
            response=f"设备控制成功: {result}"
        )
    except Exception as e:
        return ActionResponse(
            action=Action.ERROR,
            result=f"设备控制失败: {str(e)}",
            response=None
        )
```

## 📁 现有工具示例

### 1. 天气查询工具
```python
# plugins_func/functions/get_weather.py
@register_function("get_weather", GET_WEATHER_FUNCTION_DESC, ToolType.WAIT)
def get_weather(location: str = None, lang: str = "zh_CN"):
    # 天气查询逻辑
```

### 2. 音乐播放工具
```python
# plugins_func/functions/play_music.py
@register_function("play_music", play_music_function_desc, ToolType.SYSTEM_CTL)
def play_music(conn, song_name: str):
    # 音乐播放逻辑
```

### 3. 时间查询工具
```python
# plugins_func/functions/get_time.py
@register_function("get_lunar", get_lunar_function_desc, ToolType.WAIT)
def get_lunar(date=None, query=None):
    # 农历时间查询逻辑
```

## 🚀 工具开发步骤

### 1. 创建工具文件
```bash
# 在 plugins_func/functions/ 目录下创建新文件
touch plugins_func/functions/my_new_tool.py
```

### 2. 实现工具逻辑
```python
# 导入必要的模块
from plugins_func.register import register_function, ToolType, ActionResponse, Action

# 定义工具描述
tool_desc = {
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "工具功能描述",
        "parameters": {
            # 参数定义
        }
    }
}

# 注册工具
@register_function("tool_name", tool_desc, ToolType.WAIT)
def tool_function(param1, param2=None):
    # 工具实现
    pass
```

### 3. 测试工具
```python
# 创建测试脚本
def test_my_tool():
    result = my_tool("test_param")
    print(result)
```

### 4. 重启服务
```bash
# 重启小智服务器以加载新工具
python app.py
```

## 🔍 工具调试

### 1. 查看已注册工具
```python
from plugins_func.register import all_function_registry

# 打印所有已注册的工具
for name, func_item in all_function_registry.items():
    print(f"工具: {name}")
    print(f"描述: {func_item.description}")
    print(f"类型: {func_item.type}")
```

### 2. 日志调试
```python
from config.logger import setup_logging

logger = setup_logging()

@register_function("my_tool", tool_desc, ToolType.WAIT)
def my_tool(param):
    logger.info(f"工具被调用，参数: {param}")
    # 工具逻辑
```

### 3. 错误处理
```python
@register_function("my_tool", tool_desc, ToolType.WAIT)
def my_tool(param):
    try:
        # 工具逻辑
        result = process_data(param)
        return ActionResponse(Action.REQLLM, result, None)
    except ValueError as e:
        return ActionResponse(Action.ERROR, f"参数错误: {str(e)}", None)
    except Exception as e:
        return ActionResponse(Action.ERROR, f"未知错误: {str(e)}", None)
```

## 📋 工具开发最佳实践

### 1. 参数验证
```python
def my_tool(param1: str, param2: int = 10):
    # 参数验证
    if not param1 or len(param1) < 2:
        return ActionResponse(
            Action.ERROR, 
            "参数1不能为空且长度至少2个字符", 
            None
        )
    
    if param2 < 0 or param2 > 100:
        return ActionResponse(
            Action.ERROR,
            "参数2必须在0-100之间",
            None
        )
```

### 2. 缓存机制
```python
from core.utils.cache.manager import cache_manager, CacheType

def my_tool(param):
    # 检查缓存
    cache_key = f"my_tool_{param}"
    cached_result = cache_manager.get(CacheType.GENERAL, cache_key)
    if cached_result:
        return ActionResponse(Action.REQLLM, cached_result, None)
    
    # 处理逻辑
    result = process_data(param)
    
    # 缓存结果
    cache_manager.set(CacheType.GENERAL, cache_key, result)
    
    return ActionResponse(Action.REQLLM, result, None)
```

### 3. 异步处理
```python
import asyncio

@register_function("async_tool", tool_desc, ToolType.WAIT)
def async_tool(param):
    async def async_process():
        # 异步处理逻辑
        await asyncio.sleep(1)
        return f"处理完成: {param}"
    
    # 在事件循环中运行
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(async_process())
    
    return ActionResponse(Action.REQLLM, result, None)
```

## 🎯 工具类型选择指南

| 工具类型 | 适用场景 | 参数要求 | 返回方式 |
|---------|---------|---------|---------|
| `WAIT` | 数据查询、计算、分析 | 普通参数 | 请求LLM生成回复 |
| `NONE` | 日志记录、状态更新 | 普通参数 | 不返回内容 |
| `SYSTEM_CTL` | 音乐播放、系统控制 | 需要conn参数 | 直接回复或系统操作 |
| `IOT_CTL` | 设备控制、硬件操作 | 需要conn参数 | 设备状态反馈 |
| `CHANGE_SYS_PROMPT` | 角色切换、模式变更 | 普通参数 | 修改系统提示词 |

## 🔧 工具管理

### 1. 查看所有工具
```python
from plugins_func.register import all_function_registry

def list_all_tools():
    print("已注册的工具:")
    for name, func_item in all_function_registry.items():
        print(f"- {name}: {func_item.description}")
```

### 2. 动态注册工具
```python
from plugins_func.register import FunctionItem, ToolType

def register_dynamic_tool(name, description, func):
    func_item = FunctionItem(name, description, func, ToolType.WAIT)
    all_function_registry[name] = func_item
    print(f"动态注册工具: {name}")
```

### 3. 工具热重载
```python
import importlib
from plugins_func import loadplugins

def reload_tools():
    # 重新加载所有工具模块
    loadplugins.auto_import_modules('plugins_func.functions')
    print("工具已重新加载")
```

## 📚 相关文件

- `plugins_func/register.py` - 工具注册核心模块
- `plugins_func/loadplugins.py` - 自动加载工具模块
- `plugins_func/functions/` - 工具实现目录
- `core/providers/tools/` - 工具管理系统
- `data/.mcp_server_settings.json` - MCP工具配置

## 🎉 总结

小智项目提供了灵活的工具注册机制，支持：

1. **服务端插件工具** - 最常用的工具类型
2. **MCP工具** - 外部MCP服务器集成
3. **IoT设备工具** - 硬件设备控制
4. **系统控制工具** - 系统级操作

通过 `@register_function` 装饰器，可以轻松注册新工具，项目会自动加载并管理这些工具。



