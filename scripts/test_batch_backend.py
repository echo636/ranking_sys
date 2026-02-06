import requests
import json
import time

# 测试批量对抗系统的后端 API

BASE_URL = "http://localhost:8000/api/v1/batch"

candidate_list = [
    {
        "id": "leetcode",
        "name": "LeetCode",
        "info": {
            "category": "Coding Platform",
            "description": "全球最大的算法刷题平台，题目数量多，社区活跃，是大厂面试的标准题库。界面简洁，支持多种语言。"
        }
    },
    {
        "id": "codeforces",
        "name": "Codeforces",
        "info": {
            "category": "Coding Platform",
            "description": "俄罗斯的算法竞赛平台，题目难度高，侧重思维能力和数学功底。经常举办全球比赛，是ACM选手的首选训练地。"
        }
    }
]

def test_batch_flow():
    print("=" * 60)
    print("🚀 开始测试批量对抗系统")
    print("=" * 60)
    
    # 1. 测试生成场景
    print("\n[Step 1] 生成测试场景...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/generate-scenarios",
            json={
                "candidates": candidate_list,
                "num_scenarios": 3  # 测试生成3个场景
            }
        )
        
        if response.status_code != 200:
            print(f"❌ 生成失败: {response.text}")
            return
            
        data = response.json()
        scenarios = data["scenarios"]
        print(f"✅ 生成成功 ({time.time() - start_time:.2f}s)")
        print(f"生成的场景数量: {len(scenarios)}")
        
        print("\n--- 场景预览 ---")
        for i, s in enumerate(scenarios):
            print(f"Scenario {i+1} ({s['scenario_id']}):")
            print(f"Description: {s['description']}")
            print("-" * 30)
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return

    # 2. 测试批量运行
    print("\n[Step 2] 开始批量运行测试...")
    start_time = time.time()
    
    try:
        # 这里可以直接把生成的场景传回去，模拟前端流程
        payload = {
            "candidates": candidate_list,
            "scenarios": scenarios
        }
        
        # 注意：API 定义是 start_batch_tests(candidates, scenarios) 
        # 但 FastAPI 接收 JSON Body，所以需要看具体的 Body 结构
        # 我们的 API 定义是直接接收参数，还是接收 Request model？
        # 检查代码：@router.post("/start-tests") async def start_batch_tests(candidates: List[Candidate], scenarios: List[TestScenario]...)
        # 这意味着 Body 应该是 {"candidates": [...], "scenarios": [...]}
        
        response = requests.post(
            f"{BASE_URL}/start-tests",
            json=payload
        )
        
        if response.status_code != 200:
            print(f"❌ 运行失败: {response.text}")
            return
            
        result = response.json()
        print(f"✅ 运行完成 ({time.time() - start_time:.2f}s)")
        
        print("\n--- 统计结果 ---")
        print(f"总测试数: {result['total_tests']}")
        print(f"胜出统计: {result['results']}")
        print(f"胜率分布: {result['win_rate']}")
        
        print("\n--- 详细结果 ---")
        for i, detail in enumerate(result['scenario_details']):
            print(f"场景 {i+1}: {detail['winner_id']} 胜出")
            print(f"理由摘要: {detail['reasoning'][:100]}...")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    test_batch_flow()
