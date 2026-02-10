"""
Temporal Worker 入口

独立进程运行，从 Temporal Server 的 Task Queue 中轮询并执行任务。

启动方式：
    python -m app.temporal.worker

Worker 注册了所有 Workflow 和 Activity，可以处理：
- BatchRankingWorkflow (批量对抗测试)
- SingleRankWorkflow (单次排名)
- URLRankWorkflow (URL 排名)
"""

import asyncio
import logging
import sys

from temporalio.client import Client
from temporalio.worker import Worker

# 导入 Workflow 和 Activity
from app.temporal.workflows import (
    BatchRankingWorkflow,
    SingleRankWorkflow,
    URLRankWorkflow,
)
from app.temporal.activities import (
    generate_scenarios_activity,
    rank_single_scenario_activity,
    fetch_url_content_activity,
    send_webhook_notification_activity,
)
from app.core.config import settings

# 配置日志
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ranking_sys.temporal.worker")

# Task Queue 名称 - Worker 和 Client 必须使用相同的名称
TASK_QUEUE = settings.TEMPORAL_TASK_QUEUE


async def main():
    """启动 Temporal Worker"""
    logger.info(f"连接 Temporal Server: {settings.TEMPORAL_HOST}")

    # 连接 Temporal Server
    client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )

    logger.info(f"启动 Worker, Task Queue: {TASK_QUEUE}")

    # 创建 Worker
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        # 注册所有 Workflow
        workflows=[
            BatchRankingWorkflow,
            SingleRankWorkflow,
            URLRankWorkflow,
        ],
        # 注册所有 Activity
        activities=[
            generate_scenarios_activity,
            rank_single_scenario_activity,
            fetch_url_content_activity,
            send_webhook_notification_activity,
        ],
    )

    logger.info("Worker 已启动，等待任务...")

    # 运行 Worker（阻塞，直到被终止）
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
