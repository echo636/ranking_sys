import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Ranking System"
    
    # LLM Settings (支持多种 API 提供商)
    LLM_API_KEY: str
    LLM_BASE_URL: Optional[str] = None  # Optional, for custom endpoints (DeepSeek, Qwen, etc.)
    MODEL_NAME: str = "gpt-3.5-turbo"  # Default model
    
    # Token Management
    MAX_CONTEXT_TOKENS: int = 16000  # Safety limit
    TOKEN_TRUNCATION_THRESHOLD: int = 12000  # When to start truncating
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
