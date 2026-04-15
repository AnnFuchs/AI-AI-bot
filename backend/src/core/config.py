from pathlib import Path

from pydantic import EmailStr, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    """App settings."""

    app_title: str = 'AI-AI Stroke buddy.'
    app_description: str = 'Poststroke AI Assistant.'

    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_server: str
    postgres_port: int

    @field_validator('postgres_port')
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
            f'postgresql+asyncpg://{self.postgres_user}:'
            f'{self.postgres_password.get_secret_value()}'
            f'@{self.postgres_server}:'
            f'{self.postgres_port}/{self.postgres_db}'
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

    first_superuser_login: EmailStr
    first_superuser_password: SecretStr

    AI_LAYER_URL: str = "http://localhost:8001"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR.parent / 'infra' / '.env',
        env_file_encoding='utf-8',
    )


settings = Settings()
