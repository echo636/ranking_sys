"""
测试 URL 自动抓取功能 - 批量对抗测试

演示如何使用 URL 进行批量对抗测试
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_url_batch_ranking():
    """测试 URL 自动抓取 + 批量对抗测试"""
    
    print("==========================================================")
    print("测试: URL 自动抓取 + 批量场景生成")
    print("==========================================================\n")
    
    # 候选项：只提供 URL，不提供 description
    # 系统会自动抓取网页内容
    candidates = [
        {
            "id": "blog_1",
            "name": "阮一峰的网络日志",
            "info": {
                "category": "Tech Blog",
                "url": "https://www.ruanyifeng.com/blog/"
                # 注意：没有 description，系统会自动抓取
            }
        },
        {
            "id": "blog_2",
            "name": "廖雪峰的官方网站",
            "info": {
                "category": "Tech Blog",
                "url": "https://www.liaoxuefeng.com/"
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 步骤 1: 生成场景（会自动抓取 URL）
        print("📝 步骤 1: 生成测试场景...")
        print(f"候选项 1: {candidates[0]['id']} - URL: {candidates[0]['info']['url']}")
        print(f"候选项 2: {candidates[1]['id']} - URL: {candidates[1]['info']['url']}\n")
        
        response = await client.post(
            f"{BASE_URL}/api/v1/batch/generate-scenarios",
            json={
                "candidates": candidates,
                "num_scenarios": 5
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            scenarios = result['scenarios']
            print(f"[OK] 成功生成 {len(scenarios)} 个场景\n")
            
            for i, scenario in enumerate(scenarios, 1):
                print(f"场景 {i}: {scenario['description']}")
            
        else:
            print(f"[FAIL] 场景生成失败: {response.status_code}")
            print(response.text)
            return
        
        # 步骤 2: 执行批量测试（会再次检查并抓取 URL）
        print("\n" + "="*60)
        print("📊 步骤 2: 执行批量对抗测试...")
        print("="*60 + "\n")
        
        test_response = await client.post(
            f"{BASE_URL}/api/v1/batch/start-tests",
            json={
                "candidates": candidates,
                "scenarios": scenarios
            }
        )
        
        if test_response.status_code == 200:
            test_result = test_response.json()
            print("[OK] 批量测试完成！\n")
            print(f"总测试数: {test_result['total_tests']}")
            print("\n胜率统计:")
            for cand_id, rate in test_result['win_rate'].items():
                cand_name = next(c['name'] for c in candidates if c['id'] == cand_id)
                print(f"  - {cand_name}: {rate*100:.1f}%")
            
            print("\n详细结果:")
            for detail in test_result['scenario_details'][:3]:  # 显示前3个
                print(f"\n场景: {detail['scenario_description'][:50]}...")
                print(f"胜出: {detail['winner_id']}")
                print(f"耗时: {detail['processing_time']:.2f}s")
                
        else:
            print(f"[FAIL] 批量测试失败: {test_response.status_code}")
            print(test_response.text)


async def test_mixed_candidates():
    """测试混合候选项：有些有 URL，有些没有"""
    
    print("\n\n" + "="*60)
    print("测试: 混合候选项（URL + 普通描述）")
    print("="*60 + "\n")
    
    candidates = [
        {
            "id": "product_1",
            "name": "笔记本 A",
            "info": {
                "category": "Laptop",
                "description": "手动提供的描述：性能强劲的游戏本",
                "price": 8000
            }
        },
        {
            "id": "product_2",
            "name": "Python 官方文档",
            "info": {
                "category": "Documentation", 
                "url": "https://docs.python.org/zh-cn/3/"
                # 自动抓取内容
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/batch/generate-scenarios",
            json={
                "candidates": candidates,
                "num_scenarios": 3
            }
        )
        
        if response.status_code == 200:
            scenarios = response.json()['scenarios']
            print(f"[OK] 成功生成 {len(scenarios)} 个场景\n")
            for i, s in enumerate(scenarios, 1):
                print(f"{i}. {s['description']}\n")
        else:
            print(f"[FAIL] 失败: {response.status_code}")


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║  URL 自动抓取 + 批量对抗测试                                ║
║  URL Auto-Fetch + Batch Ranking Test                      ║
╚════════════════════════════════════════════════════════════╝

确保后端服务正在运行: uvicorn app.main:app --reload
    """)
    
    # 测试 1: 纯 URL 批量测试
    asyncio.run(test_url_batch_ranking())
    
    # 测试 2: 混合候选项
    print("\n")
    user_input = input("是否测试混合候选项？(y/n): ")
    if user_input.lower() == 'y':
        asyncio.run(test_mixed_candidates())
    
    print("\n[OK] 测试完成！")
