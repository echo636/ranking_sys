from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    """任务类型枚举"""
    RANK = "rank"
    RANK_URLS = "rank_urls"
    BATCH_GENERATE = "batch_generate"
    BATCH_TEST = "batch_test"
    BATCH_RUN = "batch_run"  # 合并的批量测试


class TaskSubmitResponse(BaseModel):
    """任务提交响应"""
    task_id: str = Field(..., description="任务唯一标识")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    message: str = Field(default="Task submitted successfully", description="提示信息")
    created_at: datetime = Field(..., description="创建时间")


class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    # 只在完成时返回结果
    result: Optional[Dict[str, Any]] = None


class WebhookPayload(BaseModel):
    """Webhook 通知内容"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    timestamp: datetime
    error: Optional[str] = None
