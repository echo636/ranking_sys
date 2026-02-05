# AI Ranking System

一个基于 LLM 的智能选品系统，通过 AI 分析帮助您从多个候选项中选出最佳选择。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)




## 快速开始

### 1. 环境准备

**要求**：
- Python 3.10+
- 任意 LLM API Key（OpenAI、DeepSeek、Qwen 或 Grok）

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/echo636/ranking_sys.git
cd ranking_sys

# 创建虚拟环境
conda create -n ranking_sys python=3.10
conda activate ranking_sys

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置 API

复制配置模板并填入您的 API Key：

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件
# 将 LLM_API_KEY 替换为您的真实 API Key
```

### 4. 启动后端

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

后端将运行在 http://localhost:8000

### 5. 启动前端

#### 方法 A: VS Code Live Server（推荐）
1. 安装 VS Code 扩展 "Live Server"
2. 右键 `frontend/index.html` → "Open with Live Server"

#### 方法 B: Python HTTP Server
```bash
cd frontend
python -m http.server 5500
```
访问：http://localhost:5500

### 6. 开始使用

1. 在浏览器中打开前端页面
2. 填写任务描述（例如："我要买一个适合聚会的商品，预算500元"）
3. 添加 2-3 个候选项
4. 点击"开始分析"查看 AI 推荐结果

## 使用示例

### API 调用示例

```python
import requests

payload = {
    "task_description": "我这周末要在家办一个 5 人左右的小型聚会，预算 500 元以内。",
    "candidates": [
        {
            "id": "item_1",
            "name": "JBL Go 3 蓝牙音箱",
            "info": {
                "category": "电子产品",
                "price": 299,
                "currency": "CNY",
                "description": "虽然体积小，但音量对于室内聚会足够，外观时尚。"
            }
        },
        {
            "id": "item_2",
            "name": "Switch 游戏租赁",
            "info": {
                "category": "租赁服务",
                "price": 58,
                "currency": "CNY",
                "description": "聚会气氛组神器，专门解决聚会冷场尴尬的问题。"
            }
        }
    ]
}

response = requests.post("http://localhost:8000/api/v1/rank", json=payload)
result = response.json()

print(f"最佳选择: {result['best_candidate_id']}")
print(f"理由: {result['reasoning']}")
print(f"耗时: {result['processing_time']} 秒")
```

### 响应示例

```json
{
  "best_candidate_id": "item_2",
  "reasoning": "分析用户核心需求：预算500元以内，用于5人左右的小型家庭聚会，目标是提升氛围或让大家开心...",
  "processing_time": 3.45
}
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_API_KEY` | LLM API 密钥（必需） | - |
| `LLM_BASE_URL` | API 端点 URL（可选） | None |
| `MODEL_NAME` | 模型名称 | gpt-3.5-turbo |
| `MAX_CONTEXT_TOKENS` | 最大 Token 数 | 16000 |
| `TOKEN_TRUNCATION_THRESHOLD` | 截断阈值 | 12000 |


## 测试

运行测试脚本验证 API 是否正常工作：

```bash
python scripts/test_request.py
```

## API 文档

启动后端后，访问自动生成的 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json
