from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict
from app.schemas.ranking import Candidate
from app.schemas.batch_ranking import (
    BatchRankingRequest, 
    TestScenario, 
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
    """
    generator = PromptGeneratorService(service)
    scenarios = await generator.generate_scenarios(
        candidates=request.candidates,
        num_scenarios=request.num_scenarios
    )
    return {"scenarios": scenarios}

@router.post("/start-tests", response_model=BatchRankingResult)
async def start_batch_tests(
    candidates: List[Candidate],
    scenarios: List[TestScenario],
    session_id: str = None, # 可选：用于 WebSocket 进度推送
    service: LLMService = Depends(get_llm_service)
):
    """
    开始执行批量测试 (Step 3)
    """
    processor = BatchProcessorService(service)
    
    async def progress_callback(current, total):
        if session_id:
            await manager.send_progress(session_id, current, total)
            
    result = await processor.run_batch_ranking(
        candidates=candidates,
        scenarios=scenarios,
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
