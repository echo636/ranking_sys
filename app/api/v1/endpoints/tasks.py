"""
任务管理端点

提供任务状态查询和结果获取接口。
"""

from fastapi import APIRouter, HTTPException
from app.services.task_store import get_task_store
from app.schemas.task import TaskStatusResponse, TaskStatus, TaskType

router = APIRouter()


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    - **task_id**: 任务 ID（提交任务时返回的 ID）
    
    返回任务的当前状态、创建时间、完成时间等信息。
    如果任务已完成，也会返回结果。
    """
    task_store = get_task_store()
    task = await task_store.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskStatusResponse(
        task_id=task["task_id"],
        task_type=TaskType(task["task_type"]),
        status=TaskStatus(task["status"]),
        created_at=task["created_at"],
        completed_at=task.get("completed_at"),
        error=task.get("error"),
        result=task.get("result") if task["status"] == "completed" else None
    )


@router.get("/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取任务结果
    
    - **task_id**: 任务 ID
    
    只有当任务状态为 completed 时才返回结果。
    
    状态码说明:
    - 200: 任务完成，返回结果
    - 202: 任务进行中，请稍后重试
    - 404: 任务不存在
    - 500: 任务执行失败
    """
    task_store = get_task_store()
    task = await task_store.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    status = TaskStatus(task["status"])
    
    if status == TaskStatus.PENDING:
        raise HTTPException(
            status_code=202, 
            detail="任务等待中，请稍后重试"
        )
    
    if status == TaskStatus.PROCESSING:
        raise HTTPException(
            status_code=202, 
            detail="任务处理中，请稍后重试"
        )
    
    if status == TaskStatus.FAILED:
        raise HTTPException(
            status_code=500, 
            detail=task.get("error", "任务执行失败")
        )
    
    # completed
    return task["result"]
