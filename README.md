# AI Ranking System with Temporal

基于 LLM 的智能排序系统，集成 Temporal 分布式任务队列。

## 核心功能

1. **单次排名 (Ranking)**: 对给定的候选项列表进行 LLM 排序。
2. **URL 排名 (URL Ranking)**: 自动抓取 URL 内容并进行 LLM 排序。
3. **批量对抗测试 (Batch Ranking)**:
   - 自动生成多样化测试场景
   - 并行执行大规模对抗测试
   - 统计胜率和排名结果
4. **分布式异步任务**: 使用 Temporal 编排长耗时任务，支持水平扩展。

## 快速开始

### 1. 环境准备

确保已安装 Python 3.9+ 和 Temporal CLI。

```bash
# 安装依赖
pip install -r requirements.txt
```

### 2. 启动 Temporal Server

```bash
temporal server start-dev
# Web UI: http://localhost:8233
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入 API Key：

```ini
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://api.deepseek.com/v1  # 可选
TEMPORAL_HOST=localhost:7233
```

### 4. 启动服务

**终端 1: 启动 Worker** (处理业务逻辑)
```bash
python -m app.temporal.worker
```

**终端 2: 启动 API Server** (接收请求)
```bash
uvicorn app.main:app --reload
```

## API 文档

### 同步接口 (立即返回结果)

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/ranking/rank` | 单次文本排名 |
| POST | `/api/v1/ranking/rank-urls` | URL 内容排名 |
| POST | `/api/v1/batch/generate-scenarios` | 生成测试场景 |
| POST | `/api/v1/batch/start-tests` | 执行批量测试 |

### 异步接口 (Temporal Workflow)

所有异步接口立即返回 `task_id` (即 Workflow ID)，适用于长耗时任务。

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/ranking/rank/async` | 异步单次排名 |
| POST | `/api/v1/ranking/rank-urls/async` | 异步 URL 排名 |
| POST | `/api/v1/batch/run/async` | **一键式批量测试** (生成场景+抓取+排名) |
| GET  | `/api/v1/tasks/{task_id}` | 查询任务状态 |
| GET  | `/api/v1/tasks/{task_id}/result` | 获取任务结果 |

#### 异步任务状态查询示例

1. **提交任务**:
   ```http
   POST /api/v1/batch/run/async
   {
       "candidates": [...],
       "num_scenarios": 5
   }
   ```
   *Response*: `{"task_id": "batch-run-uuid...", "status": "pending"}`

2. **查询状态**:
   ```http
   GET /api/v1/tasks/batch-run-uuid...
   ```
   *Response*: `{"status": "processing"}` -> `{"status": "completed"}`

3. **获取结果**:
   ```http
   GET /api/v1/tasks/batch-run-uuid.../result
   ```

## 项目结构

```
ranking_sys/
├── app/
│   ├── api/            # FastAPI 路由
│   ├── core/           # 配置
│   ├── services/       # 业务逻辑服务 (LLM, Scraper...)
│   ├── temporal/       # Temporal 相关代码
│   │   ├── activities.py       # Activity 定义
│   │   ├── workflows.py        # Workflow 定义
│   │   ├── worker.py           # Worker 入口
│   │   └── temporal_models.py  # 数据模型
│   └── main.py         # App 入口
├── scripts/            # 测试脚本
└── requirements.txt
```
