from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    SecretStr,
    model_validator,
)
from pydantic_extra_types.phone_numbers import PhoneNumber

from src.core.constants import Role


class UserShortInfo(BaseModel):
    """Короткая pydantic-схема для просмотра пользователя."""

    id: UUID
    username: str
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
    tg_id: str | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class UserInfo(UserShortInfo):
    """Pydantic-схема для просмотра пользователя."""

    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    """Pydantic-схема для создания пользователя."""

    username: str
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
    tg_id: str | None = None
    password: SecretStr

    @model_validator(mode='after')
    def validate_contacts(self) -> Self:
        """Проверка наличия email или телефона.

        В случае отсутствия обоих полей вызывает ValueError.
        """
        if not self.email and not self.phone:
            raise ValueError('Укажите email или телефон.')
        return self

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class AdminUserCreate(UserCreate):
    """Pydantic-схема для создания админа."""

    role: Role = Role.ADMIN


class UserUpdate(BaseModel):
    """Pydantic-схема для обновления пользователя."""

    username: str | None = None
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
    tg_id: str | None = None
    role: Role | None = None
    password: SecretStr | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')
