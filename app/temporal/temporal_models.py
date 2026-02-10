"""
Temporal 数据模型

定义 Workflow 和 Activity 的输入/输出数据类。
使用 dataclass 确保可序列化，兼容 Temporal 数据转换器。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


# ========== Activity 输入/输出 ==========

@dataclass
class CandidateData:
    """候选项序列化数据"""
    id: str
    name: str
    info: Dict  # CandidateInfo 的字典表示


@dataclass
class ScenarioData:
    """测试场景序列化数据"""
    scenario_id: str
    description: str


@dataclass
class GenerateScenariosInput:
    """场景生成 Activity 的输入"""
    candidates: List[CandidateData]
    num_scenarios: int
    custom_query: Optional[str] = None


@dataclass
class GenerateScenariosOutput:
    """场景生成 Activity 的输出"""
    scenarios: List[ScenarioData] = field(default_factory=list)


@dataclass
class RankScenarioInput:
    """单个场景排名 Activity 的输入"""
    scenario_id: str
    scenario_description: str
    candidates: List[CandidateData]


@dataclass
class RankScenarioOutput:
    """单个场景排名 Activity 的输出"""
    scenario_id: str
    scenario_description: str
    winner_id: str
    reasoning: str
    processing_time: float


@dataclass
class FetchUrlsInput:
    """URL 抓取 Activity 的输入"""
    candidates: List[CandidateData]


@dataclass
class FetchUrlsOutput:
    """URL 抓取 Activity 的输出"""
    candidates: List[CandidateData]


@dataclass
class WebhookInput:
    """Webhook 通知 Activity 的输入"""
    webhook_url: str
    workflow_id: str
    task_type: str
    status: str
    error: Optional[str] = None


# ========== Workflow 输入/输出 ==========

@dataclass
class BatchRankingWorkflowInput:
    """批量对抗测试 Workflow 的输入"""
    candidates: List[CandidateData]
    num_scenarios: int = 5
    custom_query: Optional[str] = None
    webhook_url: Optional[str] = None


@dataclass
class BatchRankingWorkflowOutput:
    """批量对抗测试 Workflow 的输出"""
    total_tests: int
    results: Dict[str, int]
    win_rate: Dict[str, float]
    scenario_details: List[RankScenarioOutput] = field(default_factory=list)


@dataclass
class SingleRankWorkflowInput:
    """单次排名 Workflow 的输入"""
    task_description: str
    candidates: List[CandidateData]
    webhook_url: Optional[str] = None


@dataclass
class SingleRankWorkflowOutput:
    """单次排名 Workflow 的输出"""
    best_candidate_id: str
    reasoning: str
    processing_time: float


@dataclass
class URLRankWorkflowInput:
    """URL 排名 Workflow 的输入"""
    task_description: str
    urls: List[str]
    webhook_url: Optional[str] = None
