from pydantic import BaseModel, ConfigDict, SecretStr


class AuthData(BaseModel):
    """Auth scheme."""

    login: str
    password: SecretStr

    model_config = ConfigDict(extra='forbid')


class AuthToken(BaseModel):
    """Token scheme."""

    access_token: str
    refresh_token: str
    token_type: str
    model_config = ConfigDict(extra="forbid")


class RefreshTokenRequest(BaseModel):
    """Refresh token scheme."""

    refresh_token: str
    model_config = ConfigDict(extra="forbid")