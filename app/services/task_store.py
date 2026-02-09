"""
任务存储服务

使用 Redis 存储异步任务状态和结果。
如果 Redis 不可用，回退到内存存储（仅用于开发）。
"""

from typing import Optional, Dict, Any
from datetime import datetime
import json
import uuid
import logging

from app.schemas.task import TaskStatus, TaskType

logger = logging.getLogger("ranking_sys")


class TaskStore:
    """任务存储服务"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self._redis_client = None
        self._memory_store: Dict[str, Dict] = {}  # 内存回退
        self.task_ttl = 86400 * 7  # 7 天过期
        self._use_redis = False
    
    async def _get_redis_client(self):
        """懒加载 Redis 客户端"""
        if self._redis_client is None and self.redis_url:
            try:
                import redis.asyncio as redis
                self._redis_client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # 测试连接
                await self._redis_client.ping()
                self._use_redis = True
                logger.info("Redis 连接成功")
            except Exception as e:
                logger.warning(f"Redis 连接失败，使用内存存储: {e}")
                self._use_redis = False
        return self._redis_client if self._use_redis else None
    
    async def create_task(
        self,
        task_type: TaskType,
        request_data: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> str:
        """创建新任务，返回 task_id"""
        task_id = str(uuid.uuid4())
        task_data = {
            "task_id": task_id,
            "task_type": task_type.value,
            "status": TaskStatus.PENDING.value,
            "request_data": request_data,
            "webhook_url": webhook_url,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "result": None,
            "error": None
        }
        
        redis_client = await self._get_redis_client()
        if redis_client:
            await redis_client.setex(
                f"task:{task_id}",
                self.task_ttl,
                json.dumps(task_data, ensure_ascii=False)
            )
        else:
            self._memory_store[task_id] = task_data
        
        logger.info(f"任务创建: {task_id} ({task_type.value})")
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        redis_client = await self._get_redis_client()
        if redis_client:
            data = await redis_client.get(f"task:{task_id}")
            if data:
                return json.loads(data)
        else:
            return self._memory_store.get(task_id)
        return None
    
    async def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """更新任务状态"""
        task = await self.get_task(task_id)
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return
        
        task["status"] = status.value
        if result is not None:
            task["result"] = result
        if error is not None:
            task["error"] = error
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task["completed_at"] = datetime.utcnow().isoformat()
        
        redis_client = await self._get_redis_client()
        if redis_client:
            await redis_client.setex(
                f"task:{task_id}",
                self.task_ttl,
                json.dumps(task, ensure_ascii=False)
            )
        else:
            self._memory_store[task_id] = task
        
        logger.info(f"任务状态更新: {task_id} -> {status.value}")
    
    async def get_webhook_url(self, task_id: str) -> Optional[str]:
        """获取任务的 webhook URL"""
        task = await self.get_task(task_id)
        if task:
            return task.get("webhook_url")
        return None


# 全局实例（延迟初始化）
_task_store: Optional[TaskStore] = None


def get_task_store() -> TaskStore:
    """获取任务存储实例"""
    global _task_store
    if _task_store is None:
        from app.core.config import settings
        redis_url = getattr(settings, 'REDIS_URL', None)
        _task_store = TaskStore(redis_url=redis_url)
    return _task_store
