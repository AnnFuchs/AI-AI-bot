from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.schemas import UserContext
from src.core.constants import AgeGroup, StrokeType
from src.users.models import User
from src.users.schemas import Medication


def _get_age_category(dob: date | None) -> AgeGroup | None:
    if not dob:
        return None
    today = date.today()
    age = (
        today.year
        - dob.year
        # subtract 1 if birthday hasn't occurred yet this year
        - ((today.month, today.day) < (dob.month, dob.day))
    )

    if age < 45:
        return AgeGroup.YOUNG

    if age <= 65:
        return AgeGroup.MIDDLE

    return AgeGroup.OLD


async def build_user_context(user: User, db: AsyncSession) -> UserContext:
    """Create context for AI layer."""
    medications = (
        [Medication(**m) for m in user.medications]
        if user.medications else None
    )

    stroke_type = (
        user.stroke_type
        if user.stroke_type and user.stroke_type != StrokeType.UNKNOWN
        else None
    )

    return UserContext(
        user_id=user.id,
        role=user.role,
        stroke_date=user.stroke_date,
        stroke_type=stroke_type,
        stroke_toast_subtype=user.stroke_toast_subtype,
        stroke_hemo_subtype=user.stroke_hemo_subtype,
        medications=medications,
        age_category=_get_age_category(user.date_of_birth),
        known_symptoms=user.known_symptoms or None,
        doctor_id=user.doctor_id,
    )
