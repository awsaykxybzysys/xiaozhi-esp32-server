import asyncio
import aiohttp
import json

async def test_stream_read():
    print("测试流式数据读取...")
    
    # API配置
    api_url = "http://localhost:8008/api/message?key=123456789"
    message = "查询流失工具的名字"
    get_url = f"{api_url}&message={message}"
    
    headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache"
    }
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            print(f"发送GET请求到: {get_url}")
            
            async with session.get(get_url, headers=headers) as response:
                print(f"响应状态码: {response.status}")
                
                if response.status == 200:
                    print("开始流式读取...")
                    chunk_count = 0
                    
                    try:
                        # 流式读取数据
                        async for line in response.content:
                            chunk_count += 1
                            if line:
                                line_str = line.decode('utf-8').strip()
                                print(f"数据块 {chunk_count}: {line_str}")
                                
                                # 检查结束信号
                                if line_str == '[DONE]' or '"message": "DONE"' in line_str:
                                    print("检测到结束信号")
                                    break
                                    
                                # 防止无限循环
                                if chunk_count > 50:
                                    print("数据块过多，停止读取")
                                    break
                            else:
                                print(f"空数据块 {chunk_count}")
                                
                    except Exception as e:
                        print(f"流式读取错误: {e}")
                        
                        # 尝试读取完整响应
                        try:
                            full_content = await response.text()
                            print(f"完整响应: {full_content}")
                        except Exception as e2:
                            print(f"读取完整响应也失败: {e2}")
                    
                    print(f"流式读取完成，共读取 {chunk_count} 个数据块")
                else:
                    error_content = await response.text()
                    print(f"错误响应: {error_content}")
                    
    except asyncio.TimeoutError:
        print("请求超时")
    except aiohttp.ClientError as e:
        print(f"网络错误: {e}")
    except Exception as e:
        print(f"其他错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_stream_read())
