from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # GigaChat
    GIGACHAT_CREDENTIALS: str = Field(default="")
    GIGACHAT_SCOPE: str = Field(default="GIGACHAT_API_PERS")
    GIGACHAT_MODEL: str = Field(default="GigaChat-2-Pro")
    GIGACHAT_EMBEDDING_MODEL: str = Field(default="EmbeddingsGigaR")

    # Таймауты (секунды)
    # fast: classifier, reminder, data_input — короткий промпт, ждём не долго
    # slow: education, wellbeing stream, clarification — могут генерировать долго
    LLM_TIMEOUT_FAST: float = Field(default=30.0)
    LLM_TIMEOUT_SLOW: float = Field(default=120.0)

    # Retry (делегируется SDK, не крутим вручную)
    LLM_MAX_RETRIES: int = Field(default=3)
    LLM_RETRY_BACKOFF_FACTOR: float = Field(default=0.5)

    # Токены — лимит истории перед отправкой в LLM
    MAX_HISTORY_TOKENS: int = Field(default=3000)

    # Qdrant
    QDRANT_URL: str = Field(default="http://localhost:6333")
    EMBEDDING_SIZE: int = Field(default=2560)  # EmbeddingsGigaR = 2560

    # App
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "extra": "ignore",
    }


settings = Settings()