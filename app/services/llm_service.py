import json
import logging
import time
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

import tiktoken
from openai import AsyncOpenAI, APIError

from app.core.config import settings
from app.core.exceptions import LLMOutputError
from app.schemas.ranking import RankingResponse, Candidate
from app.services.prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# Simple Logger
logger = logging.getLogger("ranking_sys")

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.encoder = tiktoken.get_encoding("cl100k_base") # Approximate for GPT-3.5/4

    def _estimate_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def _truncate_candidates(self, candidates: List[Candidate]) -> str:
        """
        Convert candidates to text. If too long, truncate descriptions.
        """
        # First pass: try full text
        full_text_list = []
        for idx, cand in enumerate(candidates, 1):
            # Dump info to string
            # Fix: Convert Pydantic model to dict first
            info_dict = cand.info.model_dump() 
            info_str = json.dumps(info_dict, ensure_ascii=False, indent=2)
            full_text_list.append(f"{idx}. ID: {cand.id}\n   Name: {cand.name}\n   Info: {info_str}")
        
        full_text = "\n\n".join(full_text_list)
        if self._estimate_tokens(full_text) <= settings.TOKEN_TRUNCATION_THRESHOLD:
            return full_text

        logger.warning("Input too long, applying truncation strategy...")
        
        # Second pass: Truncate description in info
        truncated_list = []
        for idx, cand in enumerate(candidates, 1):
            # Fix: Convert to dict first to modify it
            info_copy = cand.info.model_dump()
            
            # Simple heuristic: flatten or truncate known 'description' fields
            if 'description' in info_copy and isinstance(info_copy['description'], str):
                info_copy['description'] = info_copy['description'][:200] + "...(truncated)"
            
            info_str = json.dumps(info_copy, ensure_ascii=False)
            truncated_list.append(f"{idx}. ID: {cand.id}\n   Name: {cand.name}\n   Info: {info_str}")
            
        return "\n\n".join(truncated_list)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((json.JSONDecodeError, ValueError, APIError)),
        reraise=True
    )
    async def rank_candidates(self, task_description: str, candidates: List[Candidate]) -> RankingResponse:
        start_time = time.time()
        
        candidates_text = self._truncate_candidates(candidates)
        
        user_content = USER_PROMPT_TEMPLATE.format(
            task_description=task_description,
            candidates_text=candidates_text
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"}, # Force JSON mode if supported
                temperature=0.7
            )
            
            raw_content = response.choices[0].message.content
            logger.info(f"LLM Response: {raw_content[:200]}...")

            # Clean markdown code blocks if present
            clean_content = raw_content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            
            data = json.loads(clean_content)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Validate against schema and add processing_time
            return RankingResponse(
                best_candidate_id=data["best_candidate_id"],
                reasoning=data["reasoning"],
                processing_time=processing_time
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}")
            raise e
        except Exception as e:
            logger.error(f"LLM Call Failed: {e}")
            raise e
