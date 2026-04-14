from pydantic import BaseModel, ConfigDict, SecretStr


class AuthData(BaseModel):
    """Схема аутентификации."""

    login: str
    password: SecretStr

    model_config = ConfigDict(extra='forbid')


class AuthToken(BaseModel):
    """Схема получения токена."""

    access_token: str
    token_type: str

    model_config = ConfigDict(extra='forbid')
