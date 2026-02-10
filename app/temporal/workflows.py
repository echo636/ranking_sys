"""
Temporal Workflows

Workflow 只做编排逻辑，所有有副作用的操作都委托给 Activity。

Temporal 规则：
- Workflow 代码必须是确定性的
- 不能做 I/O、不能用随机数、不能访问系统时间
- 使用 workflow.execute_activity() 调度 Activity
- 使用 asyncio.gather() 实现并行执行
"""

import asyncio
from datetime import timedelta
from collections import Counter
from temporalio import workflow
from temporalio.common import RetryPolicy

# Workflow 沙箱需要通过 imports_passed_through 导入 Activity 和数据类
with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import (
        generate_scenarios_activity,
        rank_single_scenario_activity,
        fetch_url_content_activity,
        send_webhook_notification_activity,
    )
    from app.temporal.temporal_models import (
        BatchRankingWorkflowInput,
        BatchRankingWorkflowOutput,
        SingleRankWorkflowInput,
        SingleRankWorkflowOutput,
        URLRankWorkflowInput,
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


# Activity 执行的默认重试策略
DEFAULT_RETRY_POLICY = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
)


@workflow.defn(name="BatchRankingWorkflow")
class BatchRankingWorkflow:
    """
    批量对抗测试 Workflow

    编排流程：
    1. (可选) 抓取候选项的 URL 内容
    2. 使用 LLM 生成多样化测试场景
    3. 并行执行所有场景的 LLM 排名 (fan-out / fan-in)
    4. 汇总统计结果（胜率等）
    5. (可选) 发送 Webhook 通知
    """

    @workflow.run
    async def run(self, input: BatchRankingWorkflowInput) -> BatchRankingWorkflowOutput:
        candidates = input.candidates

        # Step 1: URL 内容抓取 (如果候选项包含 URL)
        fetch_result: FetchUrlsOutput = await workflow.execute_activity(
            fetch_url_content_activity,
            FetchUrlsInput(candidates=candidates),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        candidates = fetch_result.candidates

        # Step 2: 生成测试场景
        gen_result: GenerateScenariosOutput = await workflow.execute_activity(
            generate_scenarios_activity,
            GenerateScenariosInput(
                candidates=candidates,
                num_scenarios=input.num_scenarios,
                custom_query=input.custom_query,
            ),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        scenarios = gen_result.scenarios

        # Step 3: 并行执行排名 (fan-out / fan-in)
        rank_tasks = []
        for scenario in scenarios:
            rank_tasks.append(
                workflow.execute_activity(
                    rank_single_scenario_activity,
                    RankScenarioInput(
                        scenario_id=scenario.scenario_id,
                        scenario_description=scenario.description,
                        candidates=candidates,
                    ),
                    start_to_close_timeout=timedelta(seconds=90),
                    retry_policy=DEFAULT_RETRY_POLICY,
                )
            )

        rank_results: list[RankScenarioOutput] = await asyncio.gather(*rank_tasks)

        # Step 4: 汇总统计 (纯计算，直接在 Workflow 中执行)
        output = self._calculate_statistics(rank_results, candidates)

        # Step 5: Webhook 通知 (可选)
        if input.webhook_url:
            await workflow.execute_activity(
                send_webhook_notification_activity,
                WebhookInput(
                    webhook_url=input.webhook_url,
                    workflow_id=workflow.info().workflow_id,
                    task_type="batch_run",
                    status="completed",
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY_POLICY,
            )

        return output

    @staticmethod
    def _calculate_statistics(
        results: list[RankScenarioOutput],
        candidates: list[CandidateData],
    ) -> BatchRankingWorkflowOutput:
        """汇总统计胜率 - 纯计算逻辑，不含 I/O"""
        counter: Counter = Counter()

        for result in results:
            if result.winner_id != "error":
                counter[result.winner_id] += 1

        total = len(results)

        # 确保所有候选项都在 win_rate 中
        win_rate = {}
        results_count = {}
        for candidate in candidates:
            win_count = counter.get(candidate.id, 0)
            win_rate[candidate.id] = win_count / total if total > 0 else 0
            results_count[candidate.id] = win_count

        return BatchRankingWorkflowOutput(
            total_tests=total,
            results=results_count,
            win_rate=win_rate,
            scenario_details=list(results),
        )


@workflow.defn(name="SingleRankWorkflow")
class SingleRankWorkflow:
    """
    单次排名 Workflow

    流程：调用 LLM 排名 → (可选) Webhook 通知
    """

    @workflow.run
    async def run(self, input: SingleRankWorkflowInput) -> SingleRankWorkflowOutput:
        # 执行 LLM 排名
        result: RankScenarioOutput = await workflow.execute_activity(
            rank_single_scenario_activity,
            RankScenarioInput(
                scenario_id="single_rank",
                scenario_description=input.task_description,
                candidates=input.candidates,
            ),
            start_to_close_timeout=timedelta(seconds=90),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        output = SingleRankWorkflowOutput(
            best_candidate_id=result.winner_id,
            reasoning=result.reasoning,
            processing_time=result.processing_time,
        )

        # Webhook 通知
        if input.webhook_url:
            await workflow.execute_activity(
                send_webhook_notification_activity,
                WebhookInput(
                    webhook_url=input.webhook_url,
                    workflow_id=workflow.info().workflow_id,
                    task_type="rank",
                    status="completed",
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY_POLICY,
            )

        return output


@workflow.defn(name="URLRankWorkflow")
class URLRankWorkflow:
    """
    URL 排名 Workflow

    流程：抓取网页内容 → 构建候选项 → LLM 排名 → (可选) Webhook 通知
    """

    @workflow.run
    async def run(self, input: URLRankWorkflowInput) -> SingleRankWorkflowOutput:
        # Step 1: 构建候选项并抓取 URL 内容
        candidates = [
            CandidateData(
                id=f"url_{i}",
                name=url,
                info={"url": url}
            )
            for i, url in enumerate(input.urls)
        ]

        fetch_result: FetchUrlsOutput = await workflow.execute_activity(
            fetch_url_content_activity,
            FetchUrlsInput(candidates=candidates),
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        enriched_candidates = fetch_result.candidates

        # Step 2: LLM 排名
        result: RankScenarioOutput = await workflow.execute_activity(
            rank_single_scenario_activity,
            RankScenarioInput(
                scenario_id="url_rank",
                scenario_description=input.task_description,
                candidates=enriched_candidates,
            ),
            start_to_close_timeout=timedelta(seconds=90),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        output = SingleRankWorkflowOutput(
            best_candidate_id=result.winner_id,
            reasoning=result.reasoning,
            processing_time=result.processing_time,
        )

        # Webhook 通知
        if input.webhook_url:
            await workflow.execute_activity(
                send_webhook_notification_activity,
                WebhookInput(
                    webhook_url=input.webhook_url,
                    workflow_id=workflow.info().workflow_id,
                    task_type="rank_urls",
                    status="completed",
                ),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=DEFAULT_RETRY_POLICY,
            )

        return output
