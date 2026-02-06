from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from app.schemas.ranking import Candidate

# 1. 批量测试请求
class BatchRankingRequest(BaseModel):
    candidates: List[Candidate]
    num_scenarios: int = Field(5, ge=2, le=20, description="生成场景的数量，建议 5-10 个")

# 2. 测试场景
class TestScenario(BaseModel):
    scenario_id: str
    description: str = Field(..., description="具体的场景描述，包含用户身份和需求")

# 3. 场景生成响应
class ScenarioGenerationResponse(BaseModel):
    scenarios: List[TestScenario]

# 4. 单个场景的测试结果
class ScenarioResult(BaseModel):
    scenario_id: str
    scenario_description: str
    winner_id: str
    reasoning: str
    processing_time: float

# 5. 批量测试总结果
class BatchRankingResult(BaseModel):
    total_tests: int
    results: Dict[str, int]  # {"item_1": 5, "item_2": 2}
    win_rate: Dict[str, float]  # {"item_1": 0.71, ...}
    scenario_details: List[ScenarioResult]
