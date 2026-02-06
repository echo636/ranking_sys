import asyncio
from typing import List, Callable, Optional, Dict
from collections import Counter
from app.schemas.ranking import Candidate
from app.schemas.batch_ranking import TestScenario, BatchRankingResult, ScenarioResult
from app.services.llm_service import LLMService

class BatchProcessorService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def run_batch_ranking(
        self,
        candidates: List[Candidate],
        scenarios: List[TestScenario],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchRankingResult:
        """
        批量运行排名测试，支持并发控制
        """
        results: List[ScenarioResult] = []
        
        # 并发控制：同时最多运行 3 个 LLM 请求，避免触发限流
        semaphore = asyncio.Semaphore(3)
        
        # 进度计数器（使用列表以便在闭包中修改）
        completed_count = [0]
        lock = asyncio.Lock()
        
        async def process_scenario(idx: int, scenario: TestScenario) -> Optional[ScenarioResult]:
            async with semaphore:
                try:
                    import time
                    start_time = time.time()
                    
                    # 调用现有的 rank_candidates 方法
                    ranking_response = await self.llm_service.rank_candidates(
                        task_description=scenario.description,
                        candidates=candidates
                    )
                    
                    processing_time = time.time() - start_time
                    
                    result = ScenarioResult(
                        scenario_id=scenario.scenario_id,
                        scenario_description=scenario.description,
                        winner_id=ranking_response.best_candidate_id,
                        reasoning=ranking_response.reasoning,
                        processing_time=processing_time
                    )
                    
                    # 更新进度（使用锁确保线程安全）
                    async with lock:
                        completed_count[0] += 1
                        if progress_callback:
                            await progress_callback(completed_count[0], len(scenarios))
                        
                    return result
                except Exception as e:
                    print(f"Error processing scenario {scenario.scenario_id}: {e}")
                    # 记录错误但不中断整个批次
                    async with lock:
                        completed_count[0] += 1
                        if progress_callback:
                            await progress_callback(completed_count[0], len(scenarios))
                    
                    return ScenarioResult(
                        scenario_id=scenario.scenario_id,
                        scenario_description=scenario.description,
                        winner_id="error",
                        reasoning=f"Error: {str(e)}",
                        processing_time=0
                    )
        
        # 创建并发任务
        tasks = [
            process_scenario(i, s) for i, s in enumerate(scenarios)
        ]
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks)
        
        # 过滤掉 None (如果有的话)
        valid_results = [r for r in results if r is not None]
        
        # 统计结果（传入候选项列表以确保所有候选项都在结果中）
        return self._calculate_statistics(valid_results, candidates)
    
    def _calculate_statistics(self, results: List[ScenarioResult], candidates: List[Candidate]) -> BatchRankingResult:
        """统计胜率，确保所有候选项都出现在结果中"""
        counter = Counter()
        
        for result in results:
            if result.winner_id != "error":
                counter[result.winner_id] += 1
        
        total = len(results)
        
        # 确保所有候选项都在 win_rate 中，即使胜率为 0
        win_rate = {}
        for candidate in candidates:
            win_count = counter.get(candidate.id, 0)
            win_rate[candidate.id] = win_count / total if total > 0 else 0
        
        return BatchRankingResult(
            total_tests=total,
            results=dict(counter),
            win_rate=win_rate,
            scenario_details=results
        )
