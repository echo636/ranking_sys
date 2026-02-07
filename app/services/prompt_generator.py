import json
from typing import List, Optional
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
        num_scenarios: int,
        custom_query: Optional[str] = None
    ) -> List[TestScenario]:
        """
        使用 LLM 生成带"具体情境"的测试场景
        
        Args:
            candidates: 候选项列表
            num_scenarios: 要生成的场景数量
            custom_query: 可选的用户自定义 Query 模板
        """
        if custom_query:
            return await self._generate_with_template(candidates, num_scenarios, custom_query)
        else:
            return await self._generate_auto(candidates, num_scenarios)

    async def _generate_auto(
        self,
        candidates: List[Candidate],
        num_scenarios: int
    ) -> List[TestScenario]:
        """
        自动生成多样化的测试场景（原有逻辑）
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

    async def _generate_with_template(
        self,
        candidates: List[Candidate],
        num_scenarios: int,
        query_template: str
    ) -> List[TestScenario]:
        """
        基于用户提供的 Query 模板生成场景变体
        
        Args:
            candidates: 候选项列表
            num_scenarios: 生成数量
            query_template: 用户自定义的问题模板
        
        Example:
            Input: "我是{用户类型}，目标是{具体目标}，哪个更适合？"
            Output:
            - "我是准备秋招的学生，目标是通过算法面试，哪个更适合？"
            - "我是ACM选手，目标是训练高难度思维题，哪个更适合？"
        """
        candidates_text = self._format_candidates(candidates)
        
        system_prompt = f"""
        你是一个专业的场景生成助手。用户提供了一个通用问题模板：

        "{query_template}"

        你的任务是基于这个模板，生成 {num_scenarios} 个**具体的、多样化的**场景变体。
        
        要求：
        1. **保持模板结构**：核心问题框架不变
        2. **填充具体细节**：
           - 如果模板中有占位符（如 {{用户类型}}、{{目标}}），用具体内容替换
           - 如果模板是完整问题，则围绕它生成不同背景/需求的变体
        3. **确保多样性**：
           - 不同的用户身份（学生/职场人/专家/新手）
           - 不同的使用场景（时间紧急/长期规划/预算有限）
           - 不同的优先级（性能/价格/易用性/品质）
        4. **真实感**：每个场景应该像真实用户会问的问题
        
        候选项信息（供参考）：
        {candidates_text}
        """
        
        user_prompt = f"""
        请生成 {num_scenarios} 个基于模板的具体场景。
        
        输出 JSON 格式：
        {{
            "scenarios": [
                {{
                    "scenario_id": "s_1",
                    "description": "具体的场景描述..."
                }},
                ...
            ]
        }}
        """
        
        try:
            response = await self.llm_service.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,  # 稍高温度以增加变体多样性
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
            print(f"Error generating scenarios with template: {e}")
            return self._fallback_scenarios(num_scenarios)


    def _format_candidates(self, candidates: List[Candidate]) -> str:
        text = ""
        for i, c in enumerate(candidates):
            text += f"- {c.name} (ID: {c.id})\n"
            
            if hasattr(c.info, 'category') and c.info.category:
                text += f"   类别: {c.info.category}\n"
            
            if hasattr(c.info, 'price') and c.info.price is not None:
                text += f"   价格: {c.info.price}\n"
            
            # 处理 description 可能为 None 的情况
            if hasattr(c.info, 'description') and c.info.description:
                desc = c.info.description[:200]
                if len(c.info.description) > 200:
                    desc += "..."
                text += f"   描述: {desc}\n"
            
            # 如果有 URL 但没有 description，显示 URL
            if hasattr(c.info, 'url') and c.info.url and not (hasattr(c.info, 'description') and c.info.description):
                text += f"   URL: {c.info.url}\n"
            
            text += "\n"
        return text

    def _fallback_scenarios(self, count: int) -> List[TestScenario]:
        return [
            TestScenario(
                scenario_id=f"fallback_{i}", 
                description=f"这是一个通用的测试场景 {i+1}，请比较这些选项的优劣。"
            )
            for i in range(count)
        ]
