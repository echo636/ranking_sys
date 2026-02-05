from fastapi import APIRouter, HTTPException, Depends
from app.schemas.ranking import RankingRequest, RankingResponse
from app.services.llm_service import LLMService

router = APIRouter()

# Dependency for Service
def get_llm_service():
    return LLMService()

@router.post("/rank", response_model=RankingResponse)
async def rank_candidates(
    request: RankingRequest,
    service: LLMService = Depends(get_llm_service)
):
    """
    接收候选列表和任务描述，返回最佳选择。
    """
    try:
        response = await service.rank_candidates(
            task_description=request.task_description,
            candidates=request.candidates
        )
        return response
    except Exception as e:
        # In production, we should map internal exceptions to HTTP status codes carefully
        raise HTTPException(status_code=500, detail=f"Ranking failed: {str(e)}")
