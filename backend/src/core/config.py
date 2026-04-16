from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    """App settings."""

    APP_TITLE: str = 'AI-AI Stroke buddy.'
    APP_DESCRIPTION: str = 'Poststroke AI Assistant.'

    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: int
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator('POSTGRES_PORT')
    @classmethod
    def check_port(cls, value: int) -> int:
        """Port validator."""
        if not 1 <= value <= 65535:
            raise ValueError('Port number must be in range 1-65535')
        return value

    @property
    def database_url(self) -> str:
        """Db URL maker."""
        return (
            f'postgresql+asyncpg://{self.POSTGRES_USER}:'
            f'{self.POSTGRES_PASSWORD.get_secret_value()}'
            f'@{self.POSTGRES_SERVER}:'
            f'{self.POSTGRES_PORT}/{self.POSTGRES_DB}'
        )

    secret_key: SecretStr
    algorithm: str

    @property
    def jwt_auth_data(self) -> dict:
        """Generation of data for jwt."""
        return {
            'secret_key': self.secret_key.get_secret_value(),
            'algorithm': self.algorithm,
        }

    first_superuser_phone: PhoneNumber
    first_superuser_password: SecretStr

    AI_LAYER_URL: str = 'http://localhost:8001'

    model_config = SettingsConfigDict(
        env_file=BASE_DIR.parent / 'infra' / '.env',
        env_file_encoding='utf-8',
    )


settings = Settings()
