import json
from typing import List
from app.schemas.ranking import Candidate
from app.schemas.batch_ranking import TestScenario
from app.services.llm_service import LLMService
from app.core.config import settings

class PromptGeneratorService:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def generate_scenarios(
        self,
        candidates: List[Candidate],
        num_scenarios: int
    ) -> List[TestScenario]:
        """
        使用 LLM 生成带"具体情境"的测试场景
        """
        # 1. 准备候选项描述
        candidates_text = self._format_candidates(candidates)
        
        # 2. 构建 System Prompt
        system_prompt = """
        你是一个专业的评测场景设计师。你的任务是为给定的候选项生成多样化的、**带有具体情境**的测试 Prompt。
        这是为了进行 A/B 测试或多项对比测试。
        
        核心原则：
        1. **拒绝笼统**：绝对不要生成"哪个更好"、"比较A和B"这种泛泛的问题。
        2. **必须带场景**：每个 Prompt 必须包含[用户身份] + [核心需求] + [特定限制/偏好]。
        3. **多样性**：场景应覆盖不同的用户群体（新手/专家/学生/土豪）、使用环境（家庭/办公/户外）和目标（性价比/性能/耐用性）。
        4. **第一人称**：Prompt 最好以"我"开头，模拟真实用户的提问。
        
        示例模式：
        - ❌ 错误："比较 LeetCode 和 Codeforces"
        - ✅ 正确："我是一名准备秋招的计算机系大学生，只有2个月时间突击算法面试，希望题目从易到难且有大厂真题，选哪个平台刷题效率最高？"
        - ✅ 正确："我想参加 ACM 区域赛，需要高难度的思维训练题，不太在意界面美观度，应该主攻哪个平台？"
        """
        
        # 3. 构建 User Prompt
        user_prompt = f"""
        请针对以下候选项，生成 {num_scenarios} 个具体的测试场景：
        
        【候选项列表】
        {candidates_text}
        
        【输出要求】
        请只返回 JSON 格式数据，格式如下：
        {{
            "scenarios": [
                {{
                    "scenario_id": "s_1",
                    "description": "具体的场景描述文本..."
                }},
                ...
            ]
        }}
        """

        # 4. 调用 LLM
        # 假设 LLMService.client 是 AsyncOpenAI 实例
        
        try:
            response = await self.llm_service.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7, # 稍微高一点的温度以增加多样性
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            scenarios = []
            for item in data.get("scenarios", []):
                scenarios.append(TestScenario(
                    scenario_id=item.get("scenario_id", f"s_{len(scenarios)+1}"),
                    description=item.get("description", "")
                ))
                
            return scenarios
            
        except Exception as e:
            print(f"Error generating scenarios: {e}")
            # Fallback for error cases or non-JSON models
            return self._fallback_scenarios(num_scenarios)

    def _format_candidates(self, candidates: List[Candidate]) -> str:
        text = ""
        for i, c in enumerate(candidates):
            text += f"{i+1}. {c.name}\n"
            text += f"   描述: {c.info.description[:200]}...\n" # 截断避免过长
        return text

    def _fallback_scenarios(self, count: int) -> List[TestScenario]:
        return [
            TestScenario(
                scenario_id=f"fallback_{i}", 
                description=f"这是一个通用的测试场景 {i+1}，请比较这些选项的优劣。"
            )
            for i in range(count)
        ]
