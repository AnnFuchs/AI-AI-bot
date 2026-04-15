from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

# Находим корень проекта (на уровень выше папки app/)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    OPENAI_API_BASE: str = Field(default="https://api.openai.com/v1")
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL: str = Field(default="GigaEmbeddings-3B-2025-09")
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_COLLECTION_PREFIX: str = Field(default="stroke_")
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    EMBEDDING_SIZE: int = Field(default=2048)
    LLM_TIMEOUT_DEFAULT: int = 30     # classifier, reminder — короткий промпт
    LLM_TIMEOUT_SIMPLE: int = 120      # data_input
    LLM_TIMEOUT_EXTRACTION: int = 60  # каждый из 3 параллельных — они идут одновременно
    GIGACHAT_CREDENTIALS: str = Field(default="")
    GIGACHAT_SCOPE: str = Field(default="GIGACHAT_API_PERS")
    model_config = {
        "env_file": str(BASE_DIR / ".env"), 
        "extra": "ignore"
    }

settings = Settings()