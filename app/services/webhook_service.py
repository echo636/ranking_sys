"""
Webhook 通知服务

任务完成后主动调用用户提供的 webhook URL 进行通知。
"""

import httpx
import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.schemas.task import TaskStatus, TaskType, WebhookPayload

logger = logging.getLogger("ranking_sys")


class WebhookService:
    """Webhook 通知服务"""
    
    def __init__(self, max_retries: int = 3, timeout: float = 10.0):
        self.max_retries = max_retries
        self.timeout = timeout
    
    async def send_notification(
        self,
        webhook_url: str,
        task_id: str,
        task_type: TaskType,
        status: TaskStatus,
        error: Optional[str] = None
    ) -> bool:
        """
        发送 Webhook 通知
        
        Args:
            webhook_url: 回调 URL
            task_id: 任务 ID
            task_type: 任务类型
            status: 任务状态
            error: 错误信息（失败时）
            
        Returns:
            bool: 是否发送成功
        """
        payload = WebhookPayload(
            task_id=task_id,
            task_type=task_type,
            status=status,
            timestamp=datetime.utcnow(),
            error=error
        )
        
        payload_dict = payload.model_dump(mode="json")
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook_url,
                        json=payload_dict,
                        timeout=self.timeout,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Source": "ranking-sys",
                            "X-Task-Id": task_id
                        }
                    )
                    
                    if response.status_code in [200, 201, 202, 204]:
                        logger.info(
                            f"Webhook 发送成功: task={task_id}, "
                            f"url={webhook_url}, status={response.status_code}"
                        )
                        return True
                    else:
                        logger.warning(
                            f"Webhook 返回非成功状态: task={task_id}, "
                            f"status={response.status_code}"
                        )
                        
            except httpx.TimeoutException:
                logger.warning(
                    f"Webhook 超时 (尝试 {attempt + 1}/{self.max_retries}): "
                    f"task={task_id}, url={webhook_url}"
                )
            except Exception as e:
                logger.warning(
                    f"Webhook 发送失败 (尝试 {attempt + 1}/{self.max_retries}): "
                    f"task={task_id}, error={e}"
                )
            
            # 指数退避重试
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"等待 {wait_time}s 后重试...")
                await asyncio.sleep(wait_time)
        
        logger.error(
            f"Webhook 发送最终失败 (已重试 {self.max_retries} 次): "
            f"task={task_id}, url={webhook_url}"
        )
        return False


# 全局实例
webhook_service = WebhookService()
