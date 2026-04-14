from pydantic import BaseModel, ConfigDict


class AuthToken(BaseModel):
    """Схема получения токена."""

    access_token: str
    token_type: str

    model_config = ConfigDict(extra='forbid')
