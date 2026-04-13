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
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_COLLECTION_PREFIX: str = Field(default="stroke_")
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    EMBEDDING_SIZE: int = Field(default=1562)

    model_config = {
        "env_file": str(BASE_DIR / ".env"), 
        "extra": "ignore"
    }

settings = Settings()