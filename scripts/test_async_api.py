"""
异步 API 测试脚本

测试异步任务提交、状态查询和 Webhook 通知功能。
"""

import asyncio
import httpx
import time
from typing import Optional


BASE_URL = "http://localhost:8000/api/v1"


async def test_async_rank():
    """测试异步排序端点"""
    print("\n" + "=" * 50)
    print("测试 1: 异步排序 API (/rank/async)")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # 1. 提交异步任务
        response = await client.post(
            f"{BASE_URL}/rank/async",
            json={
                "task_description": "选择最适合编程学习的笔记本电脑",
                "candidates": [
                    {
                        "id": "mac",
                        "name": "MacBook Pro M3",
                        "info": {
                            "category": "笔记本",
                            "description": "苹果最新芯片，续航长，Unix系统适合开发",
                            "price": 12999
                        }
                    },
                    {
                        "id": "thinkpad",
                        "name": "ThinkPad X1 Carbon",
                        "info": {
                            "category": "笔记本",
                            "description": "商务经典，键盘手感好，Linux兼容性强",
                            "price": 9999
                        }
                    }
                ]
            }
        )
        
        print(f"提交响应状态: {response.status_code}")
        result = response.json()
        print(f"任务 ID: {result['task_id']}")
        print(f"任务状态: {result['status']}")
        
        task_id = result['task_id']
        
        # 2. 轮询任务状态
        print("\n轮询任务状态...")
        for i in range(30):  # 最多等待 30 秒
            await asyncio.sleep(1)
            
            status_response = await client.get(f"{BASE_URL}/tasks/{task_id}")
            status = status_response.json()
            
            print(f"  [{i+1}s] 状态: {status['status']}")
            
            if status['status'] == 'completed':
                print("\n[OK] 任务完成!")
                print(f"结果: {status['result']}")
                break
            elif status['status'] == 'failed':
                print(f"\n[FAIL] 任务失败: {status.get('error')}")
                break
        
        # 3. 获取结果
        print("\n获取任务结果...")
        result_response = await client.get(f"{BASE_URL}/tasks/{task_id}/result")
        if result_response.status_code == 200:
            print(f"结果: {result_response.json()}")
        else:
            print(f"获取结果失败: {result_response.status_code} - {result_response.text}")


async def test_async_batch_run():
    """测试一键式批量测试端点"""
    print("\n" + "=" * 50)
    print("测试 2: 一键式批量测试 API (/batch/run/async)")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/batch/run/async",
            json={
                "candidates": [
                    {
                        "id": "vscode",
                        "name": "VS Code",
                        "info": {
                            "category": "IDE",
                            "description": "微软开源编辑器，插件丰富，轻量级"
                        }
                    },
                    {
                        "id": "pycharm",
                        "name": "PyCharm",
                        "info": {
                            "category": "IDE",
                            "description": "JetBrains专业Python IDE，功能强大"
                        }
                    }
                ],
                "num_scenarios": 3
            }
        )
        
        print(f"提交响应状态: {response.status_code}")
        result = response.json()
        print(f"任务 ID: {result['task_id']}")
        print(f"消息: {result['message']}")
        
        task_id = result['task_id']
        
        # 轮询状态
        print("\n轮询任务状态（批量测试可能需要较长时间）...")
        for i in range(120):  # 最多等待 2 分钟
            await asyncio.sleep(2)
            
            status_response = await client.get(f"{BASE_URL}/tasks/{task_id}")
            status = status_response.json()
            
            print(f"  [{i*2}s] 状态: {status['status']}")
            
            if status['status'] == 'completed':
                print("\n[OK] 批量测试完成!")
                result_data = status['result']
                print(f"生成场景数: {len(result_data.get('scenarios', []))}")
                batch_result = result_data.get('batch_result', {})
                print(f"测试总数: {batch_result.get('total_tests')}")
                print(f"胜率: {batch_result.get('win_rate')}")
                break
            elif status['status'] == 'failed':
                print(f"\n[FAIL] 任务失败: {status.get('error')}")
                break


async def test_webhook_real():
    """实际测试 Webhook 回调"""
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    
    print("\n" + "=" * 50)
    print("测试 3: Webhook 回调测试")
    print("=" * 50)
    
    # 用于存储收到的 Webhook 数据
    webhook_received = {"data": None, "received": False}
    
    class WebhookHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            webhook_received["data"] = json.loads(post_data.decode('utf-8'))
            webhook_received["received"] = True
            
            print(f"\n[WEBHOOK] 收到 Webhook 回调!")
            print(f"   路径: {self.path}")
            print(f"   数据: {json.dumps(webhook_received['data'], indent=2, ensure_ascii=False)}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"received": true}')
        
        def log_message(self, format, *args):
            pass  # 静默日志
    
    # 启动本地 Webhook 服务器
    server = HTTPServer(('localhost', 9000), WebhookHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.daemon = True
    server_thread.start()
    
    print("[OK] 本地 Webhook 服务器已启动 (http://localhost:9000/callback)")
    
    async with httpx.AsyncClient() as client:
        # 提交带 Webhook 的异步任务
        print("\n提交异步任务 (带 webhook_url)...")
        response = await client.post(
            f"{BASE_URL}/rank/async",
            params={"webhook_url": "http://localhost:9000/callback"},
            json={
                "task_description": "测试 Webhook 回调功能",
                "candidates": [
                    {
                        "id": "opt_a",
                        "name": "选项 A",
                        "info": {"category": "测试", "description": "这是选项 A"}
                    },
                    {
                        "id": "opt_b",
                        "name": "选项 B",
                        "info": {"category": "测试", "description": "这是选项 B"}
                    }
                ]
            }
        )
        
        result = response.json()
        task_id = result['task_id']
        print(f"任务 ID: {task_id}")
        print(f"状态: {result['status']}")
        print("\n 客户端现在可以去做其他事情...")
        
        # 纯等待 Webhook 回调（不轮询）
        print("\n等待 Webhook 回调...")
        for i in range(60):  # 最多等待 60 秒
            await asyncio.sleep(0.5)
            
            if webhook_received["received"]:
                print("\n" + "=" * 40)
                print("[WEBHOOK] 收到 Webhook 通知!")
                print("=" * 40)
                print(f"   任务 ID: {webhook_received['data'].get('task_id')}")
                print(f"   任务类型: {webhook_received['data'].get('task_type')}")
                print(f"   状态: {webhook_received['data'].get('status')}")
                
                # 收到通知后获取结果
                if webhook_received['data'].get('status') == 'completed':
                    print("\n[INFO] 获取任务结果...")
                    result_resp = await client.get(f"{BASE_URL}/tasks/{task_id}/result")
                    if result_resp.status_code == 200:
                        result_data = result_resp.json()
                        print(f"   最佳选择: {result_data.get('best_candidate_id')}")
                        print(f"   理由: {result_data.get('reasoning', '')[:100]}...")
                    else:
                        print(f"   获取结果失败: {result_resp.status_code}")
                
                print("\n[OK] Webhook 测试成功!")
                break
        else:
            print("\n[FAIL] 超时：未收到 Webhook 回调")
    
    server.server_close()
    print("\n本地 Webhook 服务器已关闭")


async def main():
    print("=" * 60)
    print("  异步 API 测试脚本")
    print("  确保服务器正在运行: uvicorn app.main:app --reload")
    print("=" * 60)
    
    try:
        # 测试服务器是否运行
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8000/")
                if response.status_code == 200:
                    print("[OK] 服务器运行正常\n")
                else:
                    print("[FAIL] 服务器响应异常")
                    return
            except httpx.ConnectError:
                print("[FAIL] 无法连接服务器，请确保服务器正在运行")
                return
        
        await test_async_rank()
        # await test_async_batch_run()  # 取消注释以测试批量任务
        await test_webhook_real()  # Webhook 实际测试
        
    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
