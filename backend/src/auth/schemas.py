from pydantic import BaseModel, ConfigDict, SecretStr
from pydantic_extra_types.phone_numbers import PhoneNumber


class AuthData(BaseModel):
    """Auth scheme."""

    login: PhoneNumber
    password: SecretStr

    model_config = ConfigDict(extra='forbid')


class AuthToken(BaseModel):
    """Token scheme."""

    access_token: str
    token_type: str
    model_config = ConfigDict(extra="forbid")
