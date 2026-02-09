from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional
from datetime import datetime

from app.schemas.ranking import RankingRequest, RankingResponse, URLRankingRequest, Candidate, CandidateInfo
from app.schemas.task import TaskSubmitResponse, TaskStatus, TaskType
from app.services.llm_service import LLMService
from app.services.task_store import get_task_store
from app.services.webhook_service import webhook_service

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


# ========== 异步端点 ==========

@router.post("/rank/async", response_model=TaskSubmitResponse)
async def rank_candidates_async(
    request: RankingRequest,
    background_tasks: BackgroundTasks,
    webhook_url: Optional[str] = None
):
    """
    异步排序接口
    
    - 立即返回 task_id
    - 后台执行 LLM 排序
    - 完成后调用 webhook_url（如提供）
    
    使用方法:
    1. 调用此接口获取 task_id
    2. 等待 webhook 通知或轮询 /tasks/{task_id}
    3. 从 /tasks/{task_id}/result 获取结果
    """
    task_store = get_task_store()
    
    # 创建任务
    task_id = await task_store.create_task(
        task_type=TaskType.RANK,
        request_data=request.model_dump(),
        webhook_url=webhook_url
    )
    
    # 提交后台任务
    background_tasks.add_task(
        _execute_rank_task,
        task_id,
        request,
        webhook_url
    )
    
    return TaskSubmitResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="排序任务已提交",
        created_at=datetime.utcnow()
    )


async def _execute_rank_task(
    task_id: str,
    request: RankingRequest,
    webhook_url: Optional[str]
):
    """后台执行排序任务"""
    task_store = get_task_store()
    
    try:
        # 更新状态为处理中
        await task_store.update_status(task_id, TaskStatus.PROCESSING)
        
        # 执行排序
        service = LLMService()
        result = await service.rank_candidates(
            task_description=request.task_description,
            candidates=request.candidates
        )
        
        # 保存结果
        await task_store.update_status(
            task_id,
            TaskStatus.COMPLETED,
            result=result.model_dump()
        )
        
        # 发送 Webhook
        if webhook_url:
            await webhook_service.send_notification(
                webhook_url=webhook_url,
                task_id=task_id,
                task_type=TaskType.RANK,
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
                task_type=TaskType.RANK,
                status=TaskStatus.FAILED,
                error=str(e)
            )


@router.post("/rank-urls/async", response_model=TaskSubmitResponse)
async def rank_urls_async(
    request: URLRankingRequest,
    background_tasks: BackgroundTasks,
    webhook_url: Optional[str] = None
):
    """
    异步 URL 对比接口
    
    - 立即返回 task_id
    - 后台抓取网页并执行 LLM 排序
    - 完成后调用 webhook_url（如提供）
    """
    task_store = get_task_store()
    
    task_id = await task_store.create_task(
        task_type=TaskType.RANK_URLS,
        request_data=request.model_dump(),
        webhook_url=webhook_url
    )
    
    background_tasks.add_task(
        _execute_rank_urls_task,
        task_id,
        request,
        webhook_url
    )
    
    return TaskSubmitResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="URL 对比任务已提交",
        created_at=datetime.utcnow()
    )


async def _execute_rank_urls_task(
    task_id: str,
    request: URLRankingRequest,
    webhook_url: Optional[str]
):
    """后台执行 URL 排序任务"""
    from app.services.web_scraper import WebScraperService
    
    task_store = get_task_store()
    
    try:
        await task_store.update_status(task_id, TaskStatus.PROCESSING)
        
        # 爬取 URL
        scraper = WebScraperService(timeout=10)
        pages = await scraper.scrape_urls(request.urls)
        
        if not pages:
            raise Exception("无法爬取任何网页")
        
        # 转换为 Candidate 格式
        candidates = []
        for i, page in enumerate(pages):
            if page.get("status") == "error":
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
        
        # 调用 LLM 排序
        service = LLMService()
        result = await service.rank_candidates(
            task_description=request.task_description,
            candidates=candidates
        )
        
        # 映射回实际 URL
        for i, page in enumerate(pages):
            if result.best_candidate_id == f"url_{i}":
                result.best_candidate_id = page["url"]
                break
        
        await task_store.update_status(
            task_id,
            TaskStatus.COMPLETED,
            result=result.model_dump()
        )
        
        if webhook_url:
            await webhook_service.send_notification(
                webhook_url=webhook_url,
                task_id=task_id,
                task_type=TaskType.RANK_URLS,
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
                task_type=TaskType.RANK_URLS,
                status=TaskStatus.FAILED,
                error=str(e)
            )
