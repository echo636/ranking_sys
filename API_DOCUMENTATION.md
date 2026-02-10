# AI Ranking System - API 文档

## 概述

AI Ranking System 提供基于大语言模型的智能排序服务，支持同步和异步两种调用模式。

**核心功能**：
1. **单次排序**：基于任务描述评估多个候选项
2. **URL 对比**：自动抓取网页内容并进行对比评估
3. **批量对抗测试**：自动生成多样化场景并进行统计分析
4. **异步任务**：支持 Webhook 回调的异步处理模式


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

---

### 3. 批量对抗测试 API

#### 3.1 `POST /api/v1/batch/generate-scenarios`

生成多样化的测试场景（支持自动生成和自定义模板两种模式）。

**请求体**:
```json
{
  "candidates": [...],
  "num_scenarios": 10,
  "custom_query": "我是{用户类型}，目标是{具体目标}，应该选择哪个？"  // 可选
}
```

**响应**:
```json
{
  "scenarios": [
    {"scenario_id": "s_1", "description": "我是准备秋招的大学生..."},
    {"scenario_id": "s_2", "description": "我是职场新人..."}
  ]
}
```

#### 3.2 `POST /api/v1/batch/start-tests`

执行批量对抗测试，逐个场景调用 LLM 并统计结果。

**请求体**:
```json
{
  "candidates": [...],
  "scenarios": [{"scenario_id": "s_1", "description": "..."}],
  "session_id": "optional-session-id"
}
```

**响应**:
```json
{
  "total_tests": 10,
  "results": {"item_1": 7, "item_2": 3},
  "win_rate": {"item_1": 0.7, "item_2": 0.3},
  "scenario_details": [...]
}
```

#### 3.3 `WebSocket /api/v1/batch/ws/progress/{session_id}`

实时接收批量测试进度更新。

**消息格式**:
```json
{"current": 5, "total": 10, "percentage": 50}
```

---

### 4. 异步任务 API

### 4. 异步任务 API

异步 API 适用于长时间运行的任务。提交后立即返回任务 ID，通过 **轮询** 或 **Webhook 回调** 获取结果。
**注意**：`task_id` 即为 Temporal 的 **Workflow ID**。

**使用场景**：
- 需要立即响应用户，后台处理任务
- 外部系统集成，避免 HTTP 超时
- 批量任务处理

**通用查询参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `webhook_url` | string (可选) | 任务完成时回调的 URL |

**通用响应格式**：
```json
{
  "task_id": "fd86bc84-6039-4084-8ae7-77e26f0f4da5",
  "status": "pending",
  "message": "任务已提交，正在后台处理"
}
```

#### 4.1 `POST /api/v1/rank/async`

异步版本的排序 API。

**请求体**: 与同步版 `/rank` 相同


---

#### 4.2 `POST /api/v1/rank-urls/async`

异步版本的 URL 对比 API。

**请求体**: 与同步版 `/rank-urls` 相同

---

#### 4.3 `POST /api/v1/batch/generate-scenarios/async`

异步生成测试场景。

**请求体**: 与同步版 `/batch/generate-scenarios` 相同

---

#### 4.4 `POST /api/v1/batch/start-tests/async`

异步执行批量对抗测试。

**请求体**: 与同步版 `/batch/start-tests` 相同

---

#### 4.5 `POST /api/v1/batch/run/async`

一键批量测试（自动生成场景 + 执行测试），适合完整的自动化测试流程。

**请求体**:
```json
{
  "candidates": [
    {"id": "item_1", "name": "选项A", "info": {...}},
    {"id": "item_2", "name": "选项B", "info": {...}}
  ],
  "num_scenarios": 10,
  "custom_query": "可选的自定义模板"
}
```

**最终结果格式**（通过 `/tasks/{task_id}/result` 获取）:
```json
{
  "scenarios": [
    {"scenario_id": "s_1", "description": "..."},
    {"scenario_id": "s_2", "description": "..."}
  ],
  "batch_result": {
    "total_tests": 10,
    "results": {"item_1": 7, "item_2": 3},
    "win_rate": {"item_1": 0.7, "item_2": 0.3},
    "scenario_details": [...]
  }
}
```


---

### 5. 任务管理 API

#### 5.1 `GET /api/v1/tasks/{task_id}`

获取任务（Temporal Workflow）当前状态。

**响应**:
```json
{
  "task_id": "batch-run-uuid...",
  "status": "completed",
  "workflow_type": "BatchRankingWorkflow",
  "start_time": "2026-02-11T12:00:00+00:00",
  "close_time": "2026-02-11T12:00:10+00:00",
  "result": {...}
}
```

#### 5.2 `GET /api/v1/tasks/{task_id}/result`

获取已完成任务的结果。

**错误响应**: 
- `404` 任务不存在 
- `202` 任务进行中 (Processing)
- `500` 任务执行失败

---

### 6. Webhook 回调

任务完成时，系统会向 `webhook_url` 发送 POST 请求。

**回调格式**:
```json
{
  "task_id": "fd86bc84-...",
  "task_type": "rank",
  "status": "completed",
  "timestamp": "2026-02-09T13:09:40.842000",
  "error": null
}
```

**重试机制**: 失败后自动重试 3 次

---

## 数据模型

### Candidate (候选项)

```json
{
  "id": "string",           // 唯一标识
  "name": "string",         // 名称
  "info": {
    "category": "string",   // 可选：类别
    "description": "string",// 可选：描述
    "url": "string",        // 可选：URL（批量测试时自动抓取）
    "price": 0,             // 可选：价格
    "features": []          // 可选：特性列表
  }
}
```

### TestScenario (测试场景)

```json
{
  "scenario_id": "string",
  "description": "string"
}
```

### TaskSubmitResponse (任务提交响应)

```json
{
  "task_id": "uuid",
  "status": "pending",
  "message": "string"
}
```

### TaskStatusResponse (任务状态响应)

```json
{
  "task_id": "uuid",
  "status": "pending | processing | completed | failed",
  "workflow_type": "BatchRankingWorkflow | SingleRankWorkflow | URLRankWorkflow",
  "start_time": "datetime",
  "close_time": "datetime | null",
  "result": {}
}
```

**任务状态说明**:
| 状态 | 说明 |
|------|------|
| `pending` | 任务已提交，等待 Worker 获取 |
| `processing` | 正在执行中 (Running) |
| `completed` | 执行成功 |
| `failed` | 执行失败 (Failed / Canceled / Terminated / TimedOut) |

### WebhookPayload (Webhook 回调载荷)

```json
{
  "task_id": "uuid",
  "task_type": "string",
  "status": "completed | failed",
  "timestamp": "datetime",
  "error": "string | null"
}
```

### BatchRankingResult (批量测试结果)

```json
{
  "total_tests": 10,
  "results": {"item_1": 7, "item_2": 3},
  "win_rate": {"item_1": 0.7, "item_2": 0.3},
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
