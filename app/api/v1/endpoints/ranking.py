from fastapi import APIRouter, HTTPException, Depends
from app.schemas.ranking import RankingRequest, RankingResponse, URLRankingRequest
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
