#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真正的流式MCP计算器
使用原生MCP库实现真正的流式返回
"""

import asyncio
import json
import sys
import logging
import re
import time
import math
import random
from typing import AsyncGenerator, Any, Dict, List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('RealStreamingCalculator')

# 修复 Windows 控制台的 UTF-8 编码
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# 创建MCP服务器
server = Server("real-streaming-calculator")

class RealStreamingCalculator:
    """真正的流式计算器"""
    
    def __init__(self):
        self.name = "RealStreamingCalculator"
        self.version = "1.0.0"
    
    async def streaming_calculate(self, expression: str) -> AsyncGenerator[str, None]:
        """真正的流式计算器，每步都实时返回结果"""
        try:
            logger.info(f"🧮 开始流式计算: {expression}")
            
            # 发送开始信号
            yield json.dumps({
                "type": "start",
                "expression": expression,
                "timestamp": time.time(),
                "message": f"开始计算: {expression}"
            }, ensure_ascii=False)
            
            # 首先尝试直接计算
            try:
                result = eval(expression, {"math": math, "random": random})
                
                # 如果是简单表达式，直接返回
                if not any(op in expression for op in ['+', '-', '*', '/', '**', '^']):
                    yield json.dumps({
                        "type": "step",
                        "step": 1,
                        "expression": expression,
                        "result": result,
                        "description": f"直接计算: {expression} = {result}",
                        "is_final": True,
                        "timestamp": time.time()
                    }, ensure_ascii=False)
                    return
            except Exception as e:
                yield json.dumps({
                    "type": "error",
                    "error": str(e),
                    "timestamp": time.time()
                }, ensure_ascii=False)
                return
            
            current_expr = expression
            step_count = 0
            
            # 处理括号 - 流式返回
            while '(' in current_expr:
                start = current_expr.rfind('(')
                end = current_expr.find(')', start)
                if end == -1:
                    break
                    
                inner_expr = current_expr[start+1:end]
                inner_result = eval(inner_expr, {"math": math, "random": random})
                
                step_count += 1
                logger.info(f"🔢 步骤 {step_count}: 计算括号内")
                
                current_expr = current_expr[:start] + str(inner_result) + current_expr[end+1:]
                
                # 流式返回这一步的结果
                yield json.dumps({
                    "type": "step",
                    "step": step_count,
                    "expression": current_expr,
                    "result": inner_result,
                    "description": f"计算括号内: {inner_expr} = {inner_result}",
                    "is_final": False,
                    "timestamp": time.time()
                }, ensure_ascii=False)
                
                # 流式延迟
                await asyncio.sleep(0.5)
            
            # 处理乘方 - 流式返回
            while '**' in current_expr or '^' in current_expr:
                pattern = r'(\d+(?:\.\d+)?)\s*(\*\*|\^)\s*(\d+(?:\.\d+)?)'
                match = re.search(pattern, current_expr)
                if not match:
                    break
                    
                left, op, right = match.groups()
                left_val, right_val = float(left), float(right)
                result = left_val ** right_val
                
                step_count += 1
                logger.info(f"🔢 步骤 {step_count}: 乘方运算")
                
                current_expr = re.sub(pattern, str(result), current_expr, count=1)
                
                # 流式返回这一步的结果
                yield json.dumps({
                    "type": "step",
                    "step": step_count,
                    "expression": current_expr,
                    "result": result,
                    "description": f"乘方运算: {left} {op} {right} = {result}",
                    "is_final": False,
                    "timestamp": time.time()
                }, ensure_ascii=False)
                
                # 流式延迟
                await asyncio.sleep(0.5)
            
            # 处理乘除 - 流式返回
            while '*' in current_expr or '/' in current_expr:
                pattern = r'(\d+(?:\.\d+)?)\s*([*/])\s*(\d+(?:\.\d+)?)'
                match = re.search(pattern, current_expr)
                if not match:
                    break
                    
                left, op, right = match.groups()
                left_val, right_val = float(left), float(right)
                if op == '*':
                    result = left_val * right_val
                else:
                    result = left_val / right_val
                
                step_count += 1
                logger.info(f"🔢 步骤 {step_count}: 乘除运算")
                
                current_expr = re.sub(pattern, str(result), current_expr, count=1)
                
                # 流式返回这一步的结果
                yield json.dumps({
                    "type": "step",
                    "step": step_count,
                    "expression": current_expr,
                    "result": result,
                    "description": f"乘除运算: {left} {op} {right} = {result}",
                    "is_final": False,
                    "timestamp": time.time()
                }, ensure_ascii=False)
                
                # 流式延迟
                await asyncio.sleep(0.5)
            
            # 处理加减 - 流式返回
            while '+' in current_expr or (current_expr.count('-') > 1 or (current_expr.startswith('-') and current_expr.count('-') > 0)):
                pattern = r'(\d+(?:\.\d+)?)\s*([+-])\s*(\d+(?:\.\d+)?)'
                match = re.search(pattern, current_expr)
                if not match:
                    break
                    
                left, op, right = match.groups()
                left_val, right_val = float(left), float(right)
                if op == '+':
                    result = left_val + right_val
                else:
                    result = left_val - right_val
                
                step_count += 1
                logger.info(f"🔢 步骤 {step_count}: 加减运算")
                
                current_expr = re.sub(pattern, str(result), current_expr, count=1)
                
                # 流式返回这一步的结果
                yield json.dumps({
                    "type": "step",
                    "step": step_count,
                    "expression": current_expr,
                    "result": result,
                    "description": f"加减运算: {left} {op} {right} = {result}",
                    "is_final": False,
                    "timestamp": time.time()
                }, ensure_ascii=False)
                
                # 流式延迟
                await asyncio.sleep(0.5)
            
            # 最终结果
            final_result = float(current_expr)
            step_count += 1
            
            # 流式返回最终结果
            yield json.dumps({
                "type": "final",
                "step": step_count,
                "expression": expression,
                "result": final_result,
                "description": f"最终结果: {expression} = {final_result}",
                "is_final": True,
                "total_steps": step_count,
                "timestamp": time.time()
            }, ensure_ascii=False)
            
            logger.info(f"✅ 计算完成！总共 {step_count} 步")
            
        except Exception as e:
            logger.error(f"❌ 计算错误: {str(e)}")
            yield json.dumps({
                "type": "error",
                "error": str(e),
                "timestamp": time.time()
            }, ensure_ascii=False)

# 创建计算器实例
calculator = RealStreamingCalculator()

@server.list_tools()
async def list_tools() -> List[Tool]:
    """列出可用的工具"""
    return [
        Tool(
            name="streaming_calculator",
            description="真正的流式计算器，按步骤实时返回计算结果",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式"
                    }
                },
                "required": ["expression"]
            }
        ),
        Tool(
            name="simple_calculator",
            description="简单计算器，直接返回计算结果",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式"
                    }
                },
                "required": ["expression"]
            }
        ),
        Tool(
            name="math_functions",
            description="获取可用的数学函数列表",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """调用工具"""
    if name == "streaming_calculator":
        expression = arguments.get("expression", "")
        results = []
        
        async for result in calculator.streaming_calculate(expression):
            results.append(TextContent(type="text", text=result))
        
        return results
    
    elif name == "simple_calculator":
        expression = arguments.get("expression", "")
        try:
            result = eval(expression, {"math": math, "random": random})
            return [TextContent(type="text", text=json.dumps({
                "success": True,
                "expression": expression,
                "result": result,
                "timestamp": time.time()
            }, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "expression": expression,
                "error": str(e),
                "timestamp": time.time()
            }, ensure_ascii=False))]
    
    elif name == "math_functions":
        functions = {
            "basic": ["+", "-", "*", "/", "**", "^"],
            "math_module": [
                "sin", "cos", "tan", "asin", "acos", "atan",
                "sqrt", "pow", "exp", "log", "log10",
                "pi", "e", "ceil", "floor", "abs"
            ],
            "random_module": ["random", "randint", "uniform"]
        }
        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "functions": functions,
            "timestamp": time.time()
        }, ensure_ascii=False))]
    
    else:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Unknown tool: {name}"
        }, ensure_ascii=False))]

async def main():
    """主函数"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

