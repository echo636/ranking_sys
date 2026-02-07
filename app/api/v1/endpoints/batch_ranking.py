from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict
from app.schemas.ranking import Candidate
from app.schemas.batch_ranking import (
    BatchRankingRequest,
    BatchTestRequest,
    ScenarioGenerationResponse,
    BatchRankingResult
)
from app.services.llm_service import LLMService
from app.services.prompt_generator import PromptGeneratorService
from app.services.batch_processor import BatchProcessorService
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
