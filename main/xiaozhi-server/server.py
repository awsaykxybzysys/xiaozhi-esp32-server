#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP服务器API - 图小记
端口: 8008
功能: 间隔1秒持续输出消息，支持密钥验证
"""

import time
import threading
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json

# 设置控制台编码为UTF-8，解决Windows中文乱码问题
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

class TuXiaoJiHandler(BaseHTTPRequestHandler):
    """图小记HTTP请求处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # 获取密钥参数
        api_key = query_params.get('key', [None])[0]
        
        if path == '/api/message':
            if api_key != '123456789':
                self.send_error_response(401, "无效的密钥")
                return
            
            # 设置SSE响应头
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', 'Cache-Control')
            self.end_headers()
            
            # 持续发送消息
            self.send_continuous_messages()
            
        elif path == '/api/status':
            # 状态检查接口
            self.send_json_response(200, {
                "status": "running",
                "message": "图小记服务正常运行",
                "timestamp": int(time.time())
            })
            
        elif path == '/':
            # 根路径返回API文档
            self.send_html_response(200, self.get_api_documentation())
            
        else:
            self.send_error_response(404, "接口不存在")
    
    def send_continuous_messages(self):
        """持续发送消息，1分钟后发送结束信号"""
        try:
            count = 0
            start_time = time.time()
            duration = 20  # 60秒 = 1分钟
            
            while True:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # 检查是否已经运行了1分钟
                if elapsed_time >= duration:
                    # 发送结束信号
                    end_data = f"data: {json.dumps({'message': 'DONE', 'timestamp': int(time.time()), 'total_messages': count}, ensure_ascii=False)}\n\n"
                    self.wfile.write(end_data.encode('utf-8'))
                    self.wfile.flush()
                    print(f"已发送 {count} 条消息，发送结束信号")
                    break
                
                count += 1
                message = f"你好，我是图小记。编号: {count}"
                
                # 发送SSE格式的数据
                data = f"data: {json.dumps({'message': message, 'timestamp': int(time.time()), 'elapsed_time': round(elapsed_time, 1)}, ensure_ascii=False)}\n\n"
                self.wfile.write(data.encode('utf-8'))
                self.wfile.flush()
                
                time.sleep(1)  # 间隔1秒
                
        except (ConnectionResetError, BrokenPipeError):
            # 客户端断开连接
            print("客户端断开连接")
        except Exception as e:
            print(f"发送消息时出错: {e}")
    
    def send_json_response(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(response.encode('utf-8'))
    
    def send_html_response(self, status_code, html_content):
        """发送HTML响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def send_error_response(self, status_code, message):
        """发送错误响应"""
        self.send_json_response(status_code, {
            "error": True,
            "message": message,
            "timestamp": int(time.time())
        })
    
    def get_api_documentation(self):
        """获取API文档HTML"""
        return """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>图小记 API 文档</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #333; text-align: center; }
                .api-endpoint { background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #007bff; }
                .method { background: #007bff; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; }
                .url { font-family: monospace; background: #e9ecef; padding: 5px; border-radius: 3px; }
                .description { margin-top: 10px; color: #666; }
                .example { background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px; font-family: monospace; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 图小记 API 服务</h1>
                <p style="text-align: center; color: #666;">端口: 8008 | 密钥: 123456789</p>
                
                <div class="api-endpoint">
                    <span class="method">GET</span> <span class="url">/api/message?key=123456789</span>
                    <div class="description">
                        <strong>持续消息接口</strong><br>
                        使用Server-Sent Events (SSE)技术，间隔1秒持续输出"你好，我是图小记"消息。<br>
                        <span style="color: #28a745; font-weight: bold;">⏰ 运行1分钟后自动发送结束信号"DONE"</span>
                    </div>
                    <div class="example">
                        curl "http://localhost:8008/api/message?key=123456789"
                    </div>
                </div>
                
                <div class="api-endpoint">
                    <span class="method">GET</span> <span class="url">/api/status</span>
                    <div class="description">
                        <strong>服务状态接口</strong><br>
                        检查服务运行状态，无需密钥验证。
                    </div>
                    <div class="example">
                        curl "http://localhost:8008/api/status"
                    </div>
                </div>
                
                <div class="api-endpoint">
                    <span class="method">GET</span> <span class="url">/</span>
                    <div class="description">
                        <strong>API文档</strong><br>
                        显示此API文档页面。
                    </div>
                </div>
                
                <h3>📝 使用说明</h3>
                <ul>
                    <li>服务运行在端口 <strong>8008</strong></li>
                    <li>访问消息接口需要提供密钥参数 <strong>key=123456789</strong></li>
                    <li>消息接口使用SSE技术，会持续发送数据流</li>
                    <li>每条消息包含消息内容、时间戳和已运行时间</li>
                    <li><strong>⏰ 运行1分钟后自动发送结束信号"DONE"</strong></li>
                    <li>支持跨域访问 (CORS)</li>
                </ul>
                
                <h3>🔧 测试方法</h3>
                <p>在浏览器中打开: <a href="/api/message?key=123456789" target="_blank">/api/message?key=123456789</a></p>
            </div>
        </body>
        </html>
        """
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def run_server(port=8008):
    """启动HTTP服务器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, TuXiaoJiHandler)
    
    print(f"🚀 图小记服务启动成功!")
    print(f"📍 服务地址: http://localhost:{port}")
    print(f"🔑 密钥: 123456789")
    print(f"📡 消息接口: http://localhost:{port}/api/message?key=123456789")
    print(f"📊 状态接口: http://localhost:{port}/api/status")
    print(f"📖 API文档: http://localhost:{port}/")
    print(f"⏹️  按 Ctrl+C 停止服务")
    print("-" * 50)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
        httpd.shutdown()

if __name__ == '__main__':
    run_server()
