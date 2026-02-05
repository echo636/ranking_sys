import requests
import json
import sys

# The example data from the user's prompt
payload = {
  "task_description": "我这周末要在家办一个 5 人左右的小型聚会，预算 500 元以内。我想买点能提升聚会氛围或者让大家开心的东西，请帮我从以下选项中选一个最合适的。",
  "candidates": [
    {
      "id": "item_tech_001",
      "name": "JBL Go 3 蓝牙音箱",
      "info": {
        "category": "电子产品",
        "price": 299,
        "currency": "CNY",
        "key_features": {
          "battery_life": "5小时",
          "waterproof": "IP67防尘防水",
          "portability": "手掌大小，非常轻便"
        },
        "description": "虽然体积小，但音量对于室内聚会足够，外观时尚。",
        "user_feedback": "低音效果比预想的好，颜色很适合派对。"
      }
    },
    {
      "id": "item_food_002",
      "name": "肯德基自在厨房·整切西冷牛排 (10片装)",
      "info": {
        "category": "生鲜食品",
        "price": 199,
        "currency": "CNY",
        "key_features": {
          "quantity": "1.5kg (150g*10)",
          "cooking_method": "需要平底锅煎熟，送黄油和酱包",
          "shelf_life": "冷冻保存12个月"
        },
        "description": "聚会做大餐的硬菜，性价比极高，平均一片不到20块。",
        "user_feedback": "肉质还行，关键是方便，不用自己腌制，适合懒人聚会。"
      }
    },
    {
      "id": "item_service_003",
      "name": "任天堂 Switch 游戏租赁 (马里奥派对 + 舞力全开)",
      "info": {
        "category": "租赁服务",
        "price": 58,
        "currency": "CNY",
        "key_features": {
          "duration": "3天",
          "deposit": "需要押金 2000元 (归还后退回)",
          "content": "包含主机 + 2个游戏卡带 + 4个手柄"
        },
        "description": "聚会气氛组神器，专门解决聚会冷场尴尬的问题。",
        "user_feedback": "太值了，大家玩疯了，比只吃吃喝喝有意思多了。"
      }
    }
  ]
}

def test_ranking():
    url = "http://localhost:8000/api/v1/rank"
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        print("\n=== Success! Response ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Is it running?")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response Body: {response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_ranking()
