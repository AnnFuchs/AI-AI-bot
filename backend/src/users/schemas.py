import re
from datetime import date
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    SecretStr,
    field_validator,
)
from pydantic_extra_types.phone_numbers import PhoneNumber

from src.core.constants import (
    AgeGroup,
    EntryType,
    Role,
    Sex,
    StrokeHemSubType,
    StrokeTOASTSubType,
    StrokeType,
)


class UserCreate(BaseModel):
    """Pydantic-schema for user creation."""

    phone: PhoneNumber
    password: SecretStr

    @field_validator('password', mode='after')
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        """Check password is secure."""
        pwd = value.get_secret_value()
        pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$'
        if not re.fullmatch(pattern, pwd):
            raise ValueError(
                'Password must be at least 8 characters long and contain '
                'at least one uppercase letter,'
                'one lowercase letter, and one digit.',
            )
        return value

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class AdminUserCreate(UserCreate):
    """Pydantic-schema for admin creation."""

    role: Role = Role.ADMIN
    is_superuser: bool = True


class UserInfo(BaseModel):
    """Pydantic-schema for user info show."""

    phone: PhoneNumber
    email: EmailStr | None = None
    date_of_birth: date | None = None
    sex: Sex | None = None
    stroke_date: date | None = None
    recurrent_stroke: bool | None = None
    stroke_type: StrokeType | None = None
    stroke_toast_subtype: StrokeTOASTSubType | None = None
    stroke_hemo_subtype: StrokeHemSubType | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class UserUpdate(UserInfo):
    """Pydantic-schema for user info update."""

    phone: PhoneNumber | None = None
    role: Role | None = None


class UserContext(BaseModel):
    """Context from user."""

    user_id: UUID
    role: Role = Role.PATIENT
    stroke_date: date | None = None
    stroke_type: StrokeType | None = None
    stroke_toast_subtype: StrokeTOASTSubType | None = None
    stroke_hemo_subtype: StrokeHemSubType | None = None
    medications: list[tuple[str, int, str]] | None = None
    age_category: AgeGroup | None = None
    known_symptoms: list[str] | None = None


class DiaryEntryCreate(BaseModel):
    """Pydantic-schema for dairy entry creation."""

    entry_type: EntryType
    entry_json: dict[str, Any]

    model_config = ConfigDict(extra='forbid')
