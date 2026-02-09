"""
测试自定义 Query 模板功能

这个脚本演示如何通过 API 使用自定义 Query 模板来生成场景并运行批量测试
"""
import asyncio
import httpx
from typing import List, Dict

# API 配置
BASE_URL = "http://localhost:8000"

async def test_custom_query():
    """测试自定义 Query 模板功能"""
    
    # 1. 准备候选项
    candidates = [
        {
            "id": "leetcode",
            "name": "LeetCode",
            "info": {
                "category": "Programming Platform",
                "description": "LeetCode 是一个面试刷题平台，题目分类清晰，有大量公司真题，适合准备面试",
                "price": 0,
                "features": ["算法题库", "面试真题", "中文界面", "题解讨论"]
            }
        },
        {
            "id": "codeforces",
            "name": "Codeforces",
            "info": {
                "category": "Programming Platform",
                "description": "Codeforces 是全球知名的竞赛编程平台，题目难度高，适合 ACM/ICPC 训练",
                "price": 0,
                "features": ["竞赛题库", "Rating 系统", "实时比赛", "高难度"]
            }
        }
    ]
    
    # 2. 测试场景 1：自动生成（无自定义 Query）
    print("=" * 60)
    print("测试 1: 自动生成场景（不提供 custom_query）")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/batch/generate-scenarios",
            json={
                "candidates": candidates,
                "num_scenarios": 5
                # custom_query 不提供，使用自动生成
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 成功生成 {len(result['scenarios'])} 个场景\n")
            for i, scenario in enumerate(result['scenarios'], 1):
                print(f"场景 {i}: {scenario['description']}\n")
        else:
            print(f"[FAIL] 请求失败: {response.status_code}")
            print(response.text)
    
    # 3. 测试场景 2：使用自定义 Query 模板
    print("\n" + "=" * 60)
    print("测试 2: 使用自定义 Query 模板")
    print("=" * 60)
    
    custom_query_template = "我是{用户类型}，我的目标是{具体目标}，时间有限只有{时间限制}，应该选择哪个平台？"
    
    print(f"\n📝 自定义模板: {custom_query_template}\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/batch/generate-scenarios",
            json={
                "candidates": candidates,
                "num_scenarios": 5,
                "custom_query": custom_query_template  # 提供自定义模板
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 基于模板成功生成 {len(result['scenarios'])} 个场景变体\n")
            for i, scenario in enumerate(result['scenarios'], 1):
                print(f"场景 {i}: {scenario['description']}\n")
            
            # 保存场景以便后续批量测试
            scenarios = result['scenarios']
            
        else:
            print(f"[FAIL] 请求失败: {response.status_code}")
            print(response.text)
            return
    
    # 4. 运行批量测试（可选）
    print("\n" + "=" * 60)
    print("测试 3: 执行批量测试")
    print("=" * 60)
    
    user_input = input("\n是否继续执行批量测试？(y/n): ")
    if user_input.lower() != 'y':
        print("跳过批量测试")
        return
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/batch/start-tests",
            json={
                "candidates": candidates,
                "scenarios": scenarios
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n[OK] 批量测试完成！")
            print(f"总测试数: {result['total_tests']}")
            print(f"胜率统计:")
            for cand_id, rate in result['win_rate'].items():
                cand_name = next(c['name'] for c in candidates if c['id'] == cand_id)
                print(f"  - {cand_name}: {rate*100:.1f}%")
        else:
            print(f"[FAIL] 批量测试失败: {response.status_code}")
            print(response.text)

async def test_different_templates():
    """测试不同的 Query 模板风格"""
    
    candidates = [
        {
            "id": "laptop_a",
            "name": "MacBook Pro",
            "info": {
                "category": "Laptop",
                "description": "苹果 MacBook Pro，性能强劲，适合开发和设计",
                "price": 12000,
                "features": ["M2芯片", "16GB内存", "512GB SSD"]
            }
        },
        {
            "id": "laptop_b",
            "name": "ThinkPad X1",
            "info": {
                "category": "Laptop",
                "description": "联想 ThinkPad X1，商务笔记本，稳定可靠",
                "price": 8000,
                "features": ["Intel i7", "16GB内存", "经典键盘"]
            }
        }
    ]
    
    templates = [
        "我是{职业}，预算{预算}，主要用途是{用途}，哪个更合适？",
        "作为一个{角色}，我需要一台用于{场景}的笔记本，应该怎么选？",
        "在{具体限制}的情况下，{用户需求}，推荐哪款？"
    ]
    
    print("\n" + "=" * 60)
    print("测试 4: 测试不同的 Query 模板风格")
    print("=" * 60)
    
    for i, template in enumerate(templates, 1):
        print(f"\n📝 模板 {i}: {template}\n")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/batch/generate-scenarios",
                json={
                    "candidates": candidates,
                    "num_scenarios": 3,
                    "custom_query": template
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[OK] 生成 {len(result['scenarios'])} 个场景:")
                for j, scenario in enumerate(result['scenarios'], 1):
                    print(f"  {j}. {scenario['description']}")
            else:
                print(f"[FAIL] 失败: {response.status_code}")
        
        print()

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║  测试自定义 Query 模板功能                                  ║
║  Custom Query Template API Test                           ║
╚════════════════════════════════════════════════════════════╝

确保后端服务正在运行: uvicorn app.main:app --reload
    """)
    
    asyncio.run(test_custom_query())
    
    print("\n\n")
    test_more = input("是否测试更多模板样式？(y/n): ")
    if test_more.lower() == 'y':
        asyncio.run(test_different_templates())
    
    print("\n[OK] 测试完成！")
