#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故事播放HTTP服务器
端口: 8009
功能: 每10字输出故事内容，支持密钥验证
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

class StoryHandler(BaseHTTPRequestHandler):
    """故事播放HTTP请求处理器"""
    
    def __init__(self, *args, **kwargs):
        # 故事内容
        self.story_content = """
        从前有一个小村庄，村里住着一位善良的老爷爷。老爷爷每天都会到山上砍柴，然后到集市上卖柴火来维持生活。
        
        有一天，老爷爷在山上发现了一只受伤的小狐狸。小狐狸的腿被陷阱夹伤了，看起来很痛苦。老爷爷心生怜悯，决定帮助这只小狐狸。
        
        老爷爷小心翼翼地把小狐狸从陷阱中救出来，然后用自己衣服的布条为小狐狸包扎伤口。小狐狸虽然很害怕，但似乎能感受到老爷爷的善意，没有挣扎。
        
        从那天起，老爷爷每天都会带一些食物给小狐狸，帮助它恢复健康。渐渐地，小狐狸的伤好了，但它并没有离开，而是经常跟在老爷爷身边。
        
        村民们看到老爷爷身边总是跟着一只小狐狸，都觉得很有趣。小狐狸很聪明，它学会了帮助老爷爷捡柴火，甚至还会在集市上帮老爷爷看摊子。
        
        时间一天天过去，老爷爷和小狐狸成了最好的朋友。他们一起度过了许多快乐的时光，也一起面对了许多困难。
        
        这个故事告诉我们，善良和爱心能够创造奇迹，即使是不同种类的生物，也能成为最好的朋友。
        """.strip()
        
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # 获取密钥参数
        api_key = query_params.get('key', [None])[0]
        
        if path == '/api/story':
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
            
            # 开始播放故事
            self.play_story()
            
        elif path == '/api/status':
            # 状态检查接口
            self.send_json_response(200, {
                "status": "running",
                "message": "故事播放服务正常运行",
                "timestamp": int(time.time())
            })
            
        elif path == '/':
            # 根路径返回API文档
            self.send_html_response(200, self.get_api_documentation())
            
        else:
            self.send_error_response(404, "接口不存在")
    
    def play_story(self):
        """播放故事，每10字输出一次"""
        try:
            # 清理故事内容，移除多余的空白字符
            story_text = ' '.join(self.story_content.split())
            
            # 按10字分割故事
            chunks = self.split_text_by_length(story_text, 10)
            
            print(f"开始播放故事，总共 {len(chunks)} 段")
            
            for i, chunk in enumerate(chunks):
                # 发送故事片段
                data = {
                    "type": "story_chunk",
                    "content": chunk,
                    "chunk_number": i + 1,
                    "total_chunks": len(chunks),
                    "timestamp": int(time.time())
                }
                
                sse_data = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                self.wfile.write(sse_data.encode('utf-8'))
                self.wfile.flush()
                
                # 每段间隔0.5秒
                time.sleep(0.5)
            
            # 发送故事结束信号
            end_data = {
                "type": "story_end",
                "message": "故事播放完毕",
                "total_chunks": len(chunks),
                "timestamp": int(time.time())
            }
            
            sse_data = f"data: {json.dumps(end_data, ensure_ascii=False)}\n\n"
            self.wfile.write(sse_data.encode('utf-8'))
            self.wfile.flush()
            
            print(f"故事播放完毕，总共播放了 {len(chunks)} 段")
                
        except (ConnectionResetError, BrokenPipeError):
            # 客户端断开连接
            print("客户端断开连接")
        except Exception as e:
            print(f"播放故事时出错: {e}")
    
    def split_text_by_length(self, text, length):
        """按指定长度分割文本"""
        chunks = []
        for i in range(0, len(text), length):
            chunk = text[i:i+length]
            chunks.append(chunk)
        return chunks
    
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
            <title>故事播放 API 文档</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #333; text-align: center; }
                .api-endpoint { background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #28a745; }
                .method { background: #28a745; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; }
                .url { font-family: monospace; background: #e9ecef; padding: 5px; border-radius: 3px; }
                .description { margin-top: 10px; color: #666; }
                .example { background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px; font-family: monospace; }
                .story-preview { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #ffc107; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📚 故事播放 API 服务</h1>
                <p style="text-align: center; color: #666;">端口: 8009 | 密钥: 123456789</p>
                
                <div class="story-preview">
                    <h3>📖 故事预览</h3>
                    <p>这是一个关于善良老爷爷和受伤小狐狸的温馨故事，讲述了一段跨越物种的友谊。</p>
                </div>
                
                <div class="api-endpoint">
                    <span class="method">GET</span> <span class="url">/api/story?key=123456789</span>
                    <div class="description">
                        <strong>故事播放接口</strong><br>
                        使用Server-Sent Events (SSE)技术，每10字输出一次故事内容。<br>
                        <span style="color: #28a745; font-weight: bold;">📚 自动播放完整故事</span>
                    </div>
                    <div class="example">
                        curl "http://localhost:8009/api/story?key=123456789"
                    </div>
                </div>
                
                <div class="api-endpoint">
                    <span class="method">GET</span> <span class="url">/api/status</span>
                    <div class="description">
                        <strong>服务状态接口</strong><br>
                        检查服务运行状态，无需密钥验证。
                    </div>
                    <div class="example">
                        curl "http://localhost:8009/api/status"
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
                    <li>服务运行在端口 <strong>8009</strong></li>
                    <li>访问故事接口需要提供密钥参数 <strong>key=123456789</strong></li>
                    <li>故事接口使用SSE技术，会持续发送数据流</li>
                    <li>每10字为一段，每段间隔0.5秒</li>
                    <li>每条消息包含故事内容、段落编号和总段数</li>
                    <li>故事播放完毕后会发送结束信号</li>
                    <li>支持跨域访问 (CORS)</li>
                </ul>
                
                <h3>🔧 测试方法</h3>
                <p>在浏览器中打开: <a href="/api/story?key=123456789" target="_blank">/api/story?key=123456789</a></p>
            </div>
        </body>
        </html>
        """
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def run_server(port=8009):
    """启动HTTP服务器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, StoryHandler)
    
    print(f"📚 故事播放服务启动成功!")
    print(f"📍 服务地址: http://localhost:{port}")
    print(f"🔑 密钥: 123456789")
    print(f"📖 故事接口: http://localhost:{port}/api/story?key=123456789")
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
