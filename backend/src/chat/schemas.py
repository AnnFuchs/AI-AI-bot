from datetime import date
from uuid import UUID

from pydantic import BaseModel

from src.core.constants import (
    AgeGroup,
    Role,
    StrokeHemSubType,
    StrokeTOASTSubType,
    StrokeType,
)
from src.users.schemas import Medication


class UserContext(BaseModel):
    """Context from user."""

    user_id: UUID
    role: Role = Role.PATIENT
    stroke_date: date | None = None
    stroke_type: StrokeType | None = None
    stroke_toast_subtype: StrokeTOASTSubType | None = None
    stroke_hemo_subtype: StrokeHemSubType | None = None
    medications: list[Medication] | None = None
    age_category: AgeGroup | None = None
    known_symptoms: list[str] | None = None
    doctor_id: str | None = None


class ChatRequest(BaseModel):
    """Chat request schema."""

    session_id: UUID
    message: str
