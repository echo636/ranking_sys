# AI Ranking System

基于大语言模型的智能排序系统，提供单次排序、URL 对比和批量对抗测试功能。

## 功能特性

### 1. 单次排序 API
根据任务描述，从多个候选项中选出最佳选择。

### 2. URL 对比 API
自动抓取网页内容并进行智能对比评估。

### 3. 批量对抗测试系统 
- **场景生成**：自动生成多样化测试场景或使用自定义模板
- **批量测试**：并发执行多个场景测试，统计胜率
- **实时进度**：WebSocket 实时推送测试进度
- **URL 自动抓取**：候选项可直接使用 URL，自动抓取网页内容
- **前端界面**：可视化操作界面，支持图表展示

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件：

```bash
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4

# 或使用其他 OpenAI 兼容 API
# LLM_BASE_URL=https://api.deepseek.com/v1
# MODEL_NAME=deepseek-chat
```

### 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 访问服务

- **前端界面**: http://localhost:8000/frontend/
- **API 文档**: http://localhost:8000/docs
- **批量测试**: http://localhost:8000/frontend/batch_ranking.html

## API 使用示例

### 单次排序

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/rank",
        json={
            "task_description": "我想学习 Web 开发",
            "candidates": [
                {
                    "id": "react",
                    "name": "React",
                    "info": {"description": "由 Facebook 开发的 UI 库"}
                },
                {
                    "id": "vue",
                    "name": "Vue.js",
                    "info": {"description": "渐进式 JavaScript 框架"}
                }
            ]
        }
    )
    print(response.json())
```

### 批量对抗测试（URL 模式）

```python
# 1. 生成场景（候选项使用 URL）
scenarios_response = await client.post(
    "http://localhost:8000/api/v1/batch/generate-scenarios",
    json={
        "candidates": [
            {
                "id": "blog_1",
                "name": "阮一峰的网络日志",
                "info": {"url": "https://www.ruanyifeng.com/blog/"}
            },
            {
                "id": "blog_2",
                "name": "廖雪峰的官方网站",
                "info": {"url": "https://www.liaoxuefeng.com/"}
            }
        ],
        "num_scenarios": 10
    }
)

# 2. 执行批量测试（自动抓取 URL 内容）
test_response = await client.post(
    "http://localhost:8000/api/v1/batch/start-tests",
    json={
        "candidates": candidates,
        "scenarios": scenarios_response.json()["scenarios"]
    }
)

print(f"胜率: {test_response.json()['win_rate']}")
```

### 自定义查询模板

```python
response = await client.post(
    "http://localhost:8000/api/v1/batch/generate-scenarios",
    json={
        "candidates": candidates,
        "num_scenarios": 10,
        "custom_query": "我是{用户类型}，目标是{具体目标}，应该选择哪个？"
    }
)
```

## 测试脚本

项目提供了多个测试脚本：

```bash
# 单次排序测试
python scripts/test_ranking.py

# 批量对抗测试
python scripts/test_batch_backend.py

# 自定义模板测试
python scripts/test_custom_query.py

# URL 自动抓取测试
python scripts/test_url_batch.py
```

## 项目结构

```
ranking_sys/
├── app/
│   ├── api/v1/endpoints/      # API 端点
│   │   ├── ranking.py         # 单次排序 & URL 对比
│   │   └── batch_ranking.py   # 批量测试
│   ├── services/              # 业务逻辑
│   │   ├── llm_service.py     # LLM 调用服务
│   │   ├── web_scraper.py     # 网页抓取服务
│   │   ├── url_fetch_service.py    # URL 自动抓取
│   │   ├── prompt_generator.py     # 场景生成服务
│   │   └── batch_processor.py      # 批量处理服务
│   └── schemas/               # 数据模型
├── frontend/                  # 前端界面
│   ├── index.html            # 单次排序界面
│   └── batch_ranking.html    # 批量测试界面
├── scripts/                   # 测试脚本
└── API_DOCUMENTATION.md       # 完整 API 文档
```

## 核心功能说明

### 批量对抗测试

批量对抗测试系统可以：
1. 自动生成多样化的用户场景
2. 在每个场景下测试候选项的表现
3. 统计胜率和详细结果
4. 可视化展示对比数据


### URL 自动抓取

支持直接使用 URL 作为候选项：
- 系统自动抓取网页内容
- 提取标题、描述和正文


### 自定义查询模板

灵活定义场景生成模板：
- 使用占位符（如 `{用户类型}`）
- AI 自动生成多样化变体



## API 文档

查看完整 API 文档：
- **在线文档**: http://localhost:8000/docs
- **离线文档**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

