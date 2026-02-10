"""
任务管理端点 (Temporal)

通过 Temporal Client 查询 Workflow 状态和结果。
task_id 即 Temporal Workflow ID。
"""

from fastapi import APIRouter, HTTPException
from temporalio.client import WorkflowExecutionStatus
from temporalio.service import RPCError

from app.temporal.client import get_temporal_client

router = APIRouter()


def _map_temporal_status(status: WorkflowExecutionStatus) -> str:
    """将 Temporal Workflow 状态映射为 API 状态"""
    mapping = {
        WorkflowExecutionStatus.RUNNING: "processing",
        WorkflowExecutionStatus.COMPLETED: "completed",
        WorkflowExecutionStatus.FAILED: "failed",
        WorkflowExecutionStatus.CANCELED: "failed",
        WorkflowExecutionStatus.TERMINATED: "failed",
        WorkflowExecutionStatus.CONTINUED_AS_NEW: "processing",
        WorkflowExecutionStatus.TIMED_OUT: "failed",
    }
    return mapping.get(status, "processing")


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """
    查询任务状态 (Temporal Workflow)
    
    - **task_id**: Workflow ID（提交任务时返回的 ID）
    
    返回任务的当前状态。
    """
    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(task_id)
        desc = await handle.describe()
    except RPCError:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = _map_temporal_status(desc.status)

    response = {
        "task_id": task_id,
        "status": status,
        "workflow_type": desc.workflow_type,
        "start_time": desc.start_time.isoformat() if desc.start_time else None,
        "close_time": desc.close_time.isoformat() if desc.close_time else None,
    }

    # 如果已完成，尝试获取结果
    if status == "completed":
        try:
            result = await handle.result()
            response["result"] = result
        except Exception:
            pass

    return response


@router.get("/{task_id}/result")
async def get_task_result(task_id: str):
    """
    获取任务结果 (Temporal Workflow)
    
    - **task_id**: Workflow ID
    
    只有当 Workflow 状态为 completed 时才返回结果。
    
    状态码说明:
    - 200: 任务完成，返回结果
    - 202: 任务进行中，请稍后重试
    - 404: 任务不存在
    - 500: 任务执行失败
    """
    client = await get_temporal_client()

    try:
        handle = client.get_workflow_handle(task_id)
        desc = await handle.describe()
    except RPCError:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = _map_temporal_status(desc.status)

    if status == "processing":
        raise HTTPException(
            status_code=202,
            detail="任务处理中，请稍后重试"
        )

    if status == "failed":
        raise HTTPException(
            status_code=500,
            detail="任务执行失败"
        )

    # completed - 获取 Workflow 返回值
    try:
        result = await handle.result()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取结果失败: {str(e)}"
        )
