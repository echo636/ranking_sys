"""
Temporal Activities

将现有业务逻辑包装为 Temporal Activity。
每个 Activity 是一个独立的、可重试的、有副作用的操作单元。

Temporal 规则：
- Activity 可以做 I/O (网络请求、数据库操作等)
- Activity 应该是幂等的（可安全重试）
- Activity 内部创建服务实例，避免传递不可序列化对象
"""

import time
import logging
from typing import List
from temporalio import activity

from app.temporal.temporal_models import (
    GenerateScenariosInput,
    GenerateScenariosOutput,
    RankScenarioInput,
    RankScenarioOutput,
    FetchUrlsInput,
    FetchUrlsOutput,
    WebhookInput,
    CandidateData,
    ScenarioData,
)

logger = logging.getLogger("ranking_sys.temporal")


# ========== 辅助函数：数据转换 ==========

def _candidate_data_to_pydantic(data: CandidateData):
    """将 CandidateData dataclass 转换为 Pydantic Candidate 模型"""
    from app.schemas.ranking import Candidate, CandidateInfo
    return Candidate(
        id=data.id,
        name=data.name,
        info=CandidateInfo(**data.info)
    )


def _pydantic_to_candidate_data(candidate) -> CandidateData:
    """将 Pydantic Candidate 模型转换为 CandidateData dataclass"""
    return CandidateData(
        id=candidate.id,
        name=candidate.name,
        info=candidate.info.model_dump()
    )


# ========== Activities ==========

@activity.defn(name="generate_scenarios")
async def generate_scenarios_activity(input: GenerateScenariosInput) -> GenerateScenariosOutput:
    """
    调用 LLM 生成测试场景

    内部创建 LLMService 和 PromptGeneratorService 实例。
    """
    from app.services.llm_service import LLMService
    from app.services.prompt_generator import PromptGeneratorService

    logger.info(f"开始生成 {input.num_scenarios} 个测试场景")

    # 转换候选项数据
    candidates = [_candidate_data_to_pydantic(c) for c in input.candidates]

    # 创建服务实例并执行
    llm_service = LLMService()
    generator = PromptGeneratorService(llm_service)

    scenarios = await generator.generate_scenarios(
        candidates=candidates,
        num_scenarios=input.num_scenarios,
        custom_query=input.custom_query
    )

    # 转换输出
    scenario_list = [
        ScenarioData(
            scenario_id=s.scenario_id,
            description=s.description
        )
        for s in scenarios
    ]

    logger.info(f"成功生成 {len(scenario_list)} 个测试场景")
    return GenerateScenariosOutput(scenarios=scenario_list)


@activity.defn(name="rank_single_scenario")
async def rank_single_scenario_activity(input: RankScenarioInput) -> RankScenarioOutput:
    """
    对单个场景执行 LLM 排名

    这是批量测试中被并行调用的核心 Activity。
    每次调用都是独立的 LLM 请求，Temporal 自动管理重试。
    """
    from app.services.llm_service import LLMService

    logger.info(f"开始执行场景排名: {input.scenario_id}")
    start_time = time.time()

    # 转换候选项数据
    candidates = [_candidate_data_to_pydantic(c) for c in input.candidates]

    # 创建 LLM 服务并排名
    llm_service = LLMService()
    ranking_response = await llm_service.rank_candidates(
        task_description=input.scenario_description,
        candidates=candidates
    )

    processing_time = time.time() - start_time

    result = RankScenarioOutput(
        scenario_id=input.scenario_id,
        scenario_description=input.scenario_description,
        winner_id=ranking_response.best_candidate_id,
        reasoning=ranking_response.reasoning,
        processing_time=processing_time
    )

    logger.info(
        f"场景 {input.scenario_id} 排名完成: "
        f"winner={result.winner_id}, time={processing_time:.2f}s"
    )
    return result


@activity.defn(name="fetch_url_content")
async def fetch_url_content_activity(input: FetchUrlsInput) -> FetchUrlsOutput:
    """
    抓取 URL 内容并填充候选项描述

    检测候选项中的 URL 字段，自动抓取网页内容。
    """
    from app.services.url_fetch_service import URLFetchService

    logger.info(f"开始 URL 内容抓取, 候选项数: {len(input.candidates)}")

    # 转换候选项
    candidates = [_candidate_data_to_pydantic(c) for c in input.candidates]

    # 抓取 URL 并填充内容
    url_service = URLFetchService()
    enriched = await url_service.enrich_candidates_with_urls(candidates)

    # 转换回 dataclass
    result = FetchUrlsOutput(
        candidates=[_pydantic_to_candidate_data(c) for c in enriched]
    )

    logger.info("URL 内容抓取完成")
    return result


@activity.defn(name="send_webhook_notification")
async def send_webhook_notification_activity(input: WebhookInput) -> bool:
    """
    发送 Webhook 通知

    任务完成后主动调用用户提供的回调 URL。
    """
    from app.services.webhook_service import WebhookService
    from app.schemas.task import TaskType, TaskStatus

    logger.info(f"发送 Webhook 通知: workflow={input.workflow_id}, url={input.webhook_url}")

    webhook = WebhookService()
    success = await webhook.send_notification(
        webhook_url=input.webhook_url,
        task_id=input.workflow_id,
        task_type=TaskType(input.task_type),
        status=TaskStatus(input.status),
        error=input.error
    )

    if success:
        logger.info(f"Webhook 通知发送成功: {input.workflow_id}")
    else:
        logger.warning(f"Webhook 通知发送失败: {input.workflow_id}")

    return success
