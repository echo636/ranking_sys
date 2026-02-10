from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime

from app.schemas.ranking import RankingRequest, RankingResponse, URLRankingRequest, Candidate, CandidateInfo
from app.schemas.task import TaskSubmitResponse, TaskStatus, TaskType
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

@router.post("/rank-urls", response_model=RankingResponse)
async def rank_urls(
    request: URLRankingRequest,
    service: LLMService = Depends(get_llm_service)
):
    """
    接收 URL 列表，自动爬取网页内容并进行排名比较。
    
    - **task_description**: 评估任务描述
    - **urls**: 2-10 个 URL
    """
    from app.services.web_scraper import WebScraperService
    from app.schemas.ranking import Candidate, CandidateInfo
    
    try:
        # 爬取所有 URL
        scraper = WebScraperService(timeout=10)
        pages = await scraper.scrape_urls(request.urls)
        
        if not pages:
            raise HTTPException(status_code=400, detail="无法爬取任何网页，请检查 URL 是否有效")
        
        # 转换为 Candidate 格式
        candidates = []
        for i, page in enumerate(pages):
            if page.get("status") == "error":
                # 包含失败的URL但标记为错误
                candidates.append(
                    Candidate(
                        id=f"url_{i}",
                        name=f"{page['title']} (爬取失败)",
                        info=CandidateInfo(
                            category="网页",
                            description=page["content"]
                        )
                    )
                )
            else:
                # 成功爬取的页面
                candidates.append(
                    Candidate(
                        id=f"url_{i}",
                        name=page["title"],
                        info=CandidateInfo(
                            category="网页",
                            description=f"URL: {page['url']}\n\n{page.get('description', '')}\n\n{page['content']}"
                        )
                    )
                )
        
        # 调用 LLM 进行排名
        response = await service.rank_candidates(
            task_description=request.task_description,
            candidates=candidates
        )
        
        # 将 url_X 映射回实际 URL
        for i, page in enumerate(pages):
            if response.best_candidate_id == f"url_{i}":
                response.best_candidate_id = page["url"]
                break
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL ranking failed: {str(e)}")


# ========== 异步端点 (Temporal) ==========

@router.post("/rank/async", response_model=TaskSubmitResponse)
async def rank_candidates_async(
    request: RankingRequest,
    webhook_url: Optional[str] = None
):
    """
    异步排序接口 (Temporal Workflow)
    
    - 立即返回 task_id (即 Temporal Workflow ID)
    - Worker 进程执行 LLM 排序
    - 完成后调用 webhook_url（如提供）
    
    使用方法:
    1. 调用此接口获取 task_id
    2. 等待 webhook 通知或轮询 /tasks/{task_id}
    3. 从 /tasks/{task_id}/result 获取结果
    """
    from app.temporal.client import get_temporal_client
    from app.temporal.workflows import SingleRankWorkflow
    from app.temporal.temporal_models import SingleRankWorkflowInput, CandidateData
    from app.core.config import settings
    import uuid

    client = await get_temporal_client()

    # 转换候选项为 dataclass
    candidates_data = [
        CandidateData(id=c.id, name=c.name, info=c.info.model_dump())
        for c in request.candidates
    ]

    workflow_id = f"rank-{uuid.uuid4()}"

    # 启动 Temporal Workflow
    await client.start_workflow(
        SingleRankWorkflow.run,
        SingleRankWorkflowInput(
            task_description=request.task_description,
            candidates=candidates_data,
            webhook_url=webhook_url,
        ),
        id=workflow_id,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    )

    return TaskSubmitResponse(
        task_id=workflow_id,
        status=TaskStatus.PENDING,
        message="排序任务已提交到 Temporal",
        created_at=datetime.utcnow()
    )


@router.post("/rank-urls/async", response_model=TaskSubmitResponse)
async def rank_urls_async(
    request: URLRankingRequest,
    webhook_url: Optional[str] = None
):
    """
    异步 URL 对比接口 (Temporal Workflow)
    
    - 立即返回 task_id (即 Temporal Workflow ID)
    - Worker 进程抓取网页并执行 LLM 排序
    - 完成后调用 webhook_url（如提供）
    """
    from app.temporal.client import get_temporal_client
    from app.temporal.workflows import URLRankWorkflow
    from app.temporal.temporal_models import URLRankWorkflowInput
    from app.core.config import settings
    import uuid

    client = await get_temporal_client()

    workflow_id = f"rank-urls-{uuid.uuid4()}"

    await client.start_workflow(
        URLRankWorkflow.run,
        URLRankWorkflowInput(
            task_description=request.task_description,
            urls=request.urls,
            webhook_url=webhook_url,
        ),
        id=workflow_id,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    )

    return TaskSubmitResponse(
        task_id=workflow_id,
        status=TaskStatus.PENDING,
        message="URL 对比任务已提交到 Temporal",
        created_at=datetime.utcnow()
    )

