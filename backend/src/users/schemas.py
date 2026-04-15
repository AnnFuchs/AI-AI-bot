import re
from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_extra_types.phone_numbers import PhoneNumber

from src.core.constants import (
    Role,
    Sex,
    StrokeHemSubType,
    StrokeTOASTSubType,
    StrokeType,
)


class Medication(BaseModel):
    """Medication schema."""

    name: str
    dose_mg: int
    frequency: str

    model_config = ConfigDict(extra='forbid')


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
    doctor_id: str | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')


class UserUpdate(BaseModel):
    """Pydantic-schema for user info update."""

    phone: PhoneNumber | None = None
    email: EmailStr | None = None
    date_of_birth: date | None = None
    sex: Sex | None = None
    stroke_date: date | None = None
    recurrent_stroke: bool | None = None
    stroke_type: StrokeType | None = None
    stroke_toast_subtype: StrokeTOASTSubType | None = None
    stroke_hemo_subtype: StrokeHemSubType | None = None
    role: Role | None = None

    model_config = ConfigDict(from_attributes=True, extra='forbid')

    @model_validator(mode='after')
    def validate_stroke_subtypes(self) -> 'UserUpdate':
        """Enforce mutual exclusivity of stroke subtypes."""
        if (
            self.stroke_type == StrokeType.ISCHEMIC
            and self.stroke_hemo_subtype is not None
        ):
            raise ValueError(
                'Hemorrhagic subtype cannot be set for ischemic stroke.',
            )
        if (
            self.stroke_type == StrokeType.HEMORRHAGIC
            and self.stroke_toast_subtype is not None
        ):
            raise ValueError(
                'TOAST subtype cannot be set for hemorrhagic stroke.',
            )
        return self


class AssignDoctorUpdate(BaseModel):
    """Schema for assigning or unassigning a doctor to a patient."""

    doctor_id: str | None = None

    model_config = ConfigDict(extra='forbid')
