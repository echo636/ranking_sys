from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CandidateInfo(BaseModel):
    """商品/服务的详细信息，支持任意动态字段"""
    model_config = {"extra": "allow"} 

    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "CNY"
    description: Optional[str] = None

class Candidate(BaseModel):
    id: str = Field(..., description="候选条目的唯一标识")
    name: str = Field(..., description="候选条目名称")
    # 使用定义的 CandidateInfo 模型进行验证
    info: CandidateInfo = Field(..., description="商品的详细属性字典")

class RankingRequest(BaseModel):
    task_description: str = Field(..., description="用户的任务或需求描述")
    candidates: List[Candidate] = Field(..., description="待评估的候选列表")

class RankingResponse(BaseModel):
    best_candidate_id: str = Field(..., description="最佳选择的ID")
    reasoning: str = Field(..., description="选择该候选的详细理由（包含对比分析）")
    # 可以选择性返回其他元数据
    processing_time: float = Field(0.0, description="处理耗时(秒)")

class URLRankingRequest(BaseModel):
    """URL-based ranking request"""
    task_description: str = Field(..., description="评估任务描述，例如：比较这些技术博客的深度和质量")
    urls: List[str] = Field(..., min_length=2, max_length=10, description="待比较的URL列表（2-10个）")
