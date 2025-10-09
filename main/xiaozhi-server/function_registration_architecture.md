# 函数注册系统架构图

## 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    小智AI函数注册系统                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   插件开发层     │    │   注册管理层     │    │   执行管理层     │
│                │    │                │    │                │
│ plugins_func/   │    │ register.py     │    │ unified_tool_   │
│ functions/      │    │ loadplugins.py  │    │ handler.py      │
│                │    │                │    │                │
│ get_weather.py  │───▶│ @register_      │───▶│ ToolManager     │
│ play_music.py   │    │ function        │    │ ToolExecutor    │
│ ...             │    │ FunctionItem    │    │ ActionResponse  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 详细组件关系图

```
启动阶段:
┌─────────────────────────────────────────────────────────────────┐
│                        系统启动流程                              │
└─────────────────────────────────────────────────────────────────┘

1. UnifiedToolHandler._initialize()
   │
   ├── auto_import_modules("plugins_func.functions")
   │    │
   │    ├── 扫描 plugins_func/functions/ 目录
   │    │
   │    ├── 动态导入所有 .py 模块
   │    │
   │    └── 触发 @register_function 装饰器
   │         │
   │         └── 注册到 all_function_registry
   │              │
   │              └── 创建 FunctionItem 对象
   │
   ├── 初始化各种执行器
   │    │
   │    ├── ServerPluginExecutor
   │    ├── ServerMCPExecutor  
   │    ├── DeviceIoTExecutor
   │    └── DeviceMCPExecutor
   │
   └── 注册执行器到 ToolManager

运行时:
┌─────────────────────────────────────────────────────────────────┐
│                        工具调用流程                              │
└─────────────────────────────────────────────────────────────────┘

1. 工具调用请求
   │
   ├── UnifiedToolHandler 接收请求
   │
   ├── ToolManager.get_tool_type() 识别工具类型
   │
   ├── 选择对应的执行器
   │    │
   │    ├── ServerPluginExecutor (服务端插件)
   │    │    │
   │    │    └── 从 all_function_registry 获取函数
   │    │    │
   │    │    └── 根据 ToolType 决定参数传递方式
   │    │    │
   │    │    └── 执行函数并返回 ActionResponse
   │    │
   │    ├── ServerMCPExecutor (MCP工具)
   │    ├── DeviceIoTExecutor (IoT设备)
   │    └── DeviceMCPExecutor (设备MCP)
   │
   └── 返回执行结果
```

## 核心数据结构

### FunctionItem
```python
class FunctionItem:
    name: str              # 函数名称
    description: dict      # OpenAI格式的函数描述
    func: callable        # 实际函数对象
    type: ToolType        # 工具类型
```

### ActionResponse
```python
class ActionResponse:
    action: Action        # 动作类型 (ERROR/NOTFOUND/NONE/RESPONSE/REQLLM)
    result: Any          # 执行结果
    response: Any        # 直接回复内容
```

### ToolDefinition
```python
@dataclass
class ToolDefinition:
    name: str                    # 工具名称
    description: Dict[str, Any]  # 工具描述
    tool_type: ToolType         # 工具类型
    parameters: Optional[Dict[str, Any]] = None
```

## 工具类型映射

| 旧ToolType | 新ToolType | 说明 | 参数传递 |
|------------|------------|------|----------|
| NONE(1) | SERVER_PLUGIN | 调用完工具后，不做其他操作 | 不传conn |
| WAIT(2) | SERVER_PLUGIN | 调用工具，等待函数返回 | 不传conn |
| CHANGE_SYS_PROMPT(3) | SERVER_PLUGIN | 修改系统提示词 | 传conn |
| SYSTEM_CTL(4) | SERVER_PLUGIN | 系统控制，影响对话流程 | 传conn |
| IOT_CTL(5) | DEVICE_IOT | IOT设备控制 | 传conn |
| MCP_CLIENT(6) | SERVER_MCP | MCP客户端 | 传conn |

## 关键设计模式

1. **装饰器模式**: @register_function 用于函数注册
2. **注册表模式**: all_function_registry 作为全局函数注册表
3. **策略模式**: 不同ToolType对应不同的执行策略
4. **工厂模式**: ToolManager 根据工具类型创建对应的执行器
5. **模板方法模式**: ToolExecutor 定义执行器的标准接口

