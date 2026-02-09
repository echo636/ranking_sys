from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from typing import List, Dict, Optional
from datetime import datetime

from app.schemas.ranking import Candidate
from app.schemas.batch_ranking import (
    BatchRankingRequest,
    BatchTestRequest,
    ScenarioGenerationResponse,
    BatchRankingResult
)
from app.schemas.task import TaskSubmitResponse, TaskStatus, TaskType
from app.services.llm_service import LLMService
from app.services.prompt_generator import PromptGeneratorService
from app.services.batch_processor import BatchProcessorService
from app.services.task_store import get_task_store
from app.services.webhook_service import webhook_service
from app.api.v1.endpoints.ranking import get_llm_service

router = APIRouter()

# 简单的内存连接管理器（生产环境应使用 Redis）
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_progress(self, session_id: str, current: int, total: int):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json({
                    "current": current,
                    "total": total,
                    "percentage": int((current / total) * 100)
                })
            except Exception:
                self.disconnect(session_id)

manager = ConnectionManager()

@router.post("/generate-scenarios", response_model=ScenarioGenerationResponse)
async def generate_scenarios(
    request: BatchRankingRequest,
    service: LLMService = Depends(get_llm_service)
):
    """
    根据候选项生成测试场景 (Step 2)
    
    注意：
    - 场景生成只需要候选项的基本信息（名称、类别等）
    - URL 内容抓取会在执行测试时进行，避免重复抓取
    """
    # 生成场景（不抓取 URL，使用基本信息即可）
    generator = PromptGeneratorService(service)
    scenarios = await generator.generate_scenarios(
        candidates=request.candidates,
        num_scenarios=request.num_scenarios,
        custom_query=request.custom_query
    )
    return {"scenarios": scenarios}

@router.post("/start-tests", response_model=BatchRankingResult)
async def start_tests(
    request: BatchTestRequest,
    service: LLMService = Depends(get_llm_service)
):
    """
    执行批量对抗测试 (Step 3)

    支持 URL 自动抓取：
    - 如果候选项包含 URL 但没有描述，会自动抓取内容
    """
    from app.services.url_fetch_service import URLFetchService

    # URL 自动抓取
    url_service = URLFetchService()
    enriched_candidates = await url_service.enrich_candidates_with_urls(
        request.candidates
    )

    # 执行批量测试
    processor = BatchProcessorService(service)
    
    async def progress_callback(current, total):
        if request.session_id:
            await manager.send_progress(request.session_id, current, total)
    
    result = await processor.run_batch_ranking(
        candidates=enriched_candidates,
        scenarios=request.scenarios,
        progress_callback=progress_callback
    )
    
    return result

@router.websocket("/ws/progress/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            # 保持连接，接收客户端消息（如取消操作）
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(session_id)


# ========== 异步端点 ==========

@router.post("/generate-scenarios/async", response_model=TaskSubmitResponse)
async def generate_scenarios_async(
    request: BatchRankingRequest,
    background_tasks: BackgroundTasks,
    webhook_url: Optional[str] = None
):
    """
    异步场景生成接口
    
    - 立即返回 task_id
    - 后台执行场景生成
    - 完成后调用 webhook_url（如提供）
    """
    task_store = get_task_store()
    
    task_id = await task_store.create_task(
        task_type=TaskType.BATCH_GENERATE,
        request_data=request.model_dump(),
        webhook_url=webhook_url
    )
    
    background_tasks.add_task(
        _execute_generate_scenarios_task,
        task_id,
        request,
        webhook_url
    )
    
    return TaskSubmitResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="场景生成任务已提交",
        created_at=datetime.utcnow()
    )


async def _execute_generate_scenarios_task(
    task_id: str,
    request: BatchRankingRequest,
    webhook_url: Optional[str]
):
    """后台执行场景生成任务"""
    task_store = get_task_store()
    
    try:
        await task_store.update_status(task_id, TaskStatus.PROCESSING)
        
        service = LLMService()
        generator = PromptGeneratorService(service)
        scenarios = await generator.generate_scenarios(
            candidates=request.candidates,
            num_scenarios=request.num_scenarios,
            custom_query=request.custom_query
        )
        
        result = {"scenarios": [s.model_dump() for s in scenarios]}
        
        await task_store.update_status(
            task_id,
            TaskStatus.COMPLETED,
            result=result
        )
        
        if webhook_url:
            await webhook_service.send_notification(
                webhook_url=webhook_url,
                task_id=task_id,
                task_type=TaskType.BATCH_GENERATE,
                status=TaskStatus.COMPLETED
            )
            
    except Exception as e:
        await task_store.update_status(
            task_id,
            TaskStatus.FAILED,
            error=str(e)
        )
        
        if webhook_url:
            await webhook_service.send_notification(
                webhook_url=webhook_url,
                task_id=task_id,
                task_type=TaskType.BATCH_GENERATE,
                status=TaskStatus.FAILED,
                error=str(e)
            )


@router.post("/start-tests/async", response_model=TaskSubmitResponse)
async def start_tests_async(
    request: BatchTestRequest,
    background_tasks: BackgroundTasks,
    webhook_url: Optional[str] = None
):
    """
    异步批量测试接口
    
    - 立即返回 task_id
    - 后台执行批量测试（支持 URL 自动抓取）
    - 完成后调用 webhook_url（如提供）
    """
    task_store = get_task_store()
    
    task_id = await task_store.create_task(
        task_type=TaskType.BATCH_TEST,
        request_data=request.model_dump(),
        webhook_url=webhook_url
    )
    
    background_tasks.add_task(
        _execute_start_tests_task,
        task_id,
        request,
        webhook_url
    )
    
    return TaskSubmitResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="批量测试任务已提交",
        created_at=datetime.utcnow()
    )


async def _execute_start_tests_task(
    task_id: str,
    request: BatchTestRequest,
    webhook_url: Optional[str]
):
    """后台执行批量测试任务"""
    from app.services.url_fetch_service import URLFetchService
    
    task_store = get_task_store()
    
    try:
        await task_store.update_status(task_id, TaskStatus.PROCESSING)
        
        # URL 自动抓取
        url_service = URLFetchService()
        enriched_candidates = await url_service.enrich_candidates_with_urls(
            request.candidates
        )
        
        # 执行批量测试
        service = LLMService()
        processor = BatchProcessorService(service)
        
        result = await processor.run_batch_ranking(
            candidates=enriched_candidates,
            scenarios=request.scenarios,
            progress_callback=None  # 异步模式不支持 WebSocket 进度
        )
        
        await task_store.update_status(
            task_id,
            TaskStatus.COMPLETED,
            result=result.model_dump()
        )
        
        if webhook_url:
            await webhook_service.send_notification(
                webhook_url=webhook_url,
                task_id=task_id,
                task_type=TaskType.BATCH_TEST,
                status=TaskStatus.COMPLETED
            )
            
    except Exception as e:
        await task_store.update_status(
            task_id,
            TaskStatus.FAILED,
            error=str(e)
        )
        
        if webhook_url:
            await webhook_service.send_notification(
                webhook_url=webhook_url,
                task_id=task_id,
                task_type=TaskType.BATCH_TEST,
                status=TaskStatus.FAILED,
                error=str(e)
            )


@router.post("/run/async", response_model=TaskSubmitResponse)
async def batch_run_async(
    request: BatchRankingRequest,
    background_tasks: BackgroundTasks,
    webhook_url: Optional[str] = None
):
    """
    一键式批量测试接口（合并端点）
    
    自动执行：
    1. 生成测试场景
    2. 执行批量测试
    
    - 立即返回 task_id
    - 后台完成全部流程
    - 完成后调用 webhook_url（如提供）
    """
    task_store = get_task_store()
    
    task_id = await task_store.create_task(
        task_type=TaskType.BATCH_RUN,
        request_data=request.model_dump(),
        webhook_url=webhook_url
    )
    
    background_tasks.add_task(
        _execute_batch_run_task,
        task_id,
        request,
        webhook_url
    )
    
    return TaskSubmitResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="一键式批量测试任务已提交",
        created_at=datetime.utcnow()
    )


async def _execute_batch_run_task(
    task_id: str,
    request: BatchRankingRequest,
    webhook_url: Optional[str]
):
    """后台执行一键式批量测试任务"""
    from app.services.url_fetch_service import URLFetchService
    
    task_store = get_task_store()
    
    try:
        await task_store.update_status(task_id, TaskStatus.PROCESSING)
        
        service = LLMService()
        
        # Step 1: 生成场景
        generator = PromptGeneratorService(service)
        scenarios = await generator.generate_scenarios(
            candidates=request.candidates,
            num_scenarios=request.num_scenarios,
            custom_query=request.custom_query
        )
        
        # Step 2: URL 自动抓取
        url_service = URLFetchService()
        enriched_candidates = await url_service.enrich_candidates_with_urls(
            request.candidates
        )
        
        # Step 3: 执行批量测试
        processor = BatchProcessorService(service)
        batch_result = await processor.run_batch_ranking(
            candidates=enriched_candidates,
            scenarios=scenarios,
            progress_callback=None
        )
        
        # 合并结果
        result = {
            "scenarios": [s.model_dump() for s in scenarios],
            "batch_result": batch_result.model_dump()
        }
        
        await task_store.update_status(
            task_id,
            TaskStatus.COMPLETED,
            result=result
        )
        
        if webhook_url:
            await webhook_service.send_notification(
                webhook_url=webhook_url,
                task_id=task_id,
                task_type=TaskType.BATCH_RUN,
                status=TaskStatus.COMPLETED
            )
            
    except Exception as e:
        await task_store.update_status(
            task_id,
            TaskStatus.FAILED,
            error=str(e)
        )
        
        if webhook_url:
            await webhook_service.send_notification(
                webhook_url=webhook_url,
                task_id=task_id,
                task_type=TaskType.BATCH_RUN,
                status=TaskStatus.FAILED,
                error=str(e)
            )

