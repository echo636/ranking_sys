# AI Ranking System - API 文档

## 概述

AI Ranking System 提供基于大语言模型的智能排序服务，支持三种核心功能：
1. **单次排序**：基于任务描述评估多个候选项
2. **URL 对比**：自动抓取网页内容并进行对比评估
3. **批量对抗测试**：自动生成多样化场景并进行统计分析


## API 端点列表

### 1. 单次排序 API

#### `POST /api/v1/rank`

根据任务描述，从候选项中选出最佳选择。

**请求体**:
```json
{
  "task_description": "我想学习 Web 开发，需要选择一个前端框架",
  "candidates": [
    {
      "id": "react",
      "name": "React",
      "info": {
        "category": "Frontend Framework",
        "description": "由 Facebook 开发的声明式 UI 库",
        "price": 0,
        "features": ["组件化", "虚拟DOM", "生态丰富"]
      }
    },
    {
      "id": "vue",
      "name": "Vue.js",
      "info": {
        "category": "Frontend Framework",
        "description": "渐进式 JavaScript 框架",
        "price": 0,
        "features": ["易学易用", "双向绑定", "中文文档"]
      }
    }
  ]
}
```

**响应**:
```json
{
  "best_candidate_id": "vue",
  "reasoning": "对于 Web 开发初学者，Vue.js 更适合...",
  "processing_time": 1.23
}
```

**Python 示例**:
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/rank",
        json={
            "task_description": "我想学习 Web 开发",
            "candidates": [...]
        }
    )
    result = response.json()
    print(f"推荐: {result['best_candidate_id']}")
```

---

### 2. URL 对比 API

#### `POST /api/v1/rank-urls`

自动抓取多个 URL 的内容并进行对比评估。

**请求体**:
```json
{
  "task_description": "比较这些技术博客的深度和实用性",
  "urls": [
    "https://example.com/blog1",
    "https://example.com/blog2"
  ]
}
```

**响应**:
```json
{
  "best_candidate_id": "url_1",
  "reasoning": "第一篇博客在技术深度和代码示例方面更出色...",
  "processing_time": 3.45
}
```

**限制**:
- 最少 2 个 URL，最多 10 个
- 仅支持静态网页（无 JavaScript 渲染）
- 超时时间：10 秒/URL

**curl 示例**:
```bash
curl -X POST http://localhost:8000/api/v1/rank-urls \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "比较技术博客质量",
    "urls": ["https://example1.com", "https://example2.com"]
  }'
```

---

### 3. 批量对抗测试 API

批量对抗系统提供三个核心端点，用于生成场景、执行批量测试和实时进度跟踪。

#### 3.1 `POST /api/v1/batch/generate-scenarios`

生成多样化的测试场景（支持自动生成和自定义模板两种模式）。

**请求体（自动生成模式）**:
```json
{
  "candidates": [
    {
      "id": "item_1",
      "name": "选项 A",
      "info": {
        "category": "Product",
        "description": "详细描述...",
        "price": 100
      }
    }
  ],
  "num_scenarios": 10
}
```

**请求体（自定义模板模式）**:
```json
{
  "candidates": [...],
  "num_scenarios": 10,
  "custom_query": "我是{用户类型}，目标是{具体目标}，应该选择哪个？"
}
```

**响应**:
```json
{
  "scenarios": [
    {
      "scenario_id": "s_1",
      "description": "我是准备秋招的大学生，需要在 2 个月内快速提升算法能力..."
    },
    {
      "scenario_id": "s_2",
      "description": "我是职场新人，每天只有 1 小时刷题时间..."
    }
  ]
}
```

**Python 示例**:
```python
# 自动生成
response = await client.post(
    "http://localhost:8000/api/v1/batch/generate-scenarios",
    json={
        "candidates": candidates,
        "num_scenarios": 10
    }
)

# 自定义模板
response = await client.post(
    "http://localhost:8000/api/v1/batch/generate-scenarios",
    json={
        "candidates": candidates,
        "num_scenarios": 10,
        "custom_query": "我是{用户}，需要{功能}，哪个更好？"
    }
)
```

#### 3.2 `POST /api/v1/batch/start-tests`

执行批量对抗测试，逐个场景调用 LLM 并统计结果。

**请求体**:
```json
{
  "candidates": [...],
  "scenarios": [
    {
      "scenario_id": "s_1",
      "description": "具体场景描述"
    }
  ],
  "session_id": "optional-session-id"
}
```

**响应**:
```json
{
  "total_tests": 10,
  "results": {
    "item_1": 7,
    "item_2": 3
  },
  "win_rate": {
    "item_1": 0.7,
    "item_2": 0.3
  },
  "scenario_details": [
    {
      "scenario_id": "s_1",
      "scenario_description": "...",
      "winner_id": "item_1",
      "reasoning": "...",
      "processing_time": 1.2
    }
  ]
}
```

**Python 示例**:
```python
result = await client.post(
    "http://localhost:8000/api/v1/batch/start-tests",
    json={
        "candidates": candidates,
        "scenarios": scenarios,
        "session_id": "test-123"  # 可选，用于 WebSocket 进度推送
    },
    timeout=120.0
)

print(f"总测试: {result['total_tests']}")
for cand_id, rate in result['win_rate'].items():
    print(f"{cand_id}: {rate*100:.1f}%")
```

#### 3.3 `WebSocket /api/v1/batch/ws/progress/{session_id}`

实时接收批量测试进度更新。

**连接**:
```javascript
const ws = new WebSocket(
  `ws://localhost:8000/api/v1/batch/ws/progress/${sessionId}`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`进度: ${data.current}/${data.total} (${data.percentage}%)`);
};
```

**消息格式**:
```json
{
  "current": 5,
  "total": 10,
  "percentage": 50
}
```

**Python 示例**:
```python
import asyncio
import websockets

async def track_progress(session_id):
    uri = f"ws://localhost:8000/api/v1/batch/ws/progress/{session_id}"
    async with websockets.connect(uri) as ws:
        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(f"进度: {data['percentage']}%")
```

---

## 数据模型

### Candidate (候选项)

```python
{
  "id": str,           # 唯一标识
  "name": str,         # 名称
  "info": {            # 详细信息
    "category": str,   # 可选：类别
    "description": str,# 可选：描述
    "price": float,    # 可选：价格
    "features": list   # 可选：特性列表
    # 支持任意自定义字段
  }
}
```

### TestScenario (测试场景)

```python
{
  "scenario_id": str,      # 场景 ID
  "description": str       # 场景描述（模拟真实用户提问）
}
```

### BatchRankingResult (批量测试结果)

```python
{
  "total_tests": int,           # 总测试数
  "results": {                  # 每个候选项的胜场数
    "item_1": int,
    "item_2": int
  },
  "win_rate": {                 # 胜率统计
    "item_1": float,
    "item_2": float
  },
  "scenario_details": [         # 每个场景的详细结果
    {
      "scenario_id": str,
      "scenario_description": str,
      "winner_id": str,
      "reasoning": str,
      "processing_time": float
    }
  ]
}
```

