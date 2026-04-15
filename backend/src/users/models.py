from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Date, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import (
    DOC_ID_LEN,
    EMAIL_LEN,
    PASSW_HASH_LEN,
    PHONE_LEN,
    Role,
    Sex,
    StrokeHemSubType,
    StrokeTOASTSubType,
    StrokeType,
)
from src.db.base import Base, CommonMixin

if TYPE_CHECKING:
    from src.diary.models import DiaryEntry


class User(CommonMixin, Base):
    """Basic User."""

    __tablename__ = 'users'

    phone: Mapped[str] = mapped_column(
        String(PHONE_LEN),
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str | None] = mapped_column(
        String(EMAIL_LEN),
        unique=True,
        index=True,
        nullable=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(PASSW_HASH_LEN),
        nullable=False,
    )
    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    sex: Mapped[Sex] = mapped_column(
        Enum(Sex, name='sex_enum'),
        default=Sex.UNKNOWN,
        nullable=False,
    )
    role: Mapped[Role] = mapped_column(
        Enum(Role, name='role_enum'),
        default=Role.PATIENT,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    stroke_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    recurrent_stroke: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    stroke_type: Mapped[StrokeType] = mapped_column(
        Enum(StrokeType, name='stroke_type_enum'),
        default=StrokeType.UNKNOWN,
        nullable=False,
    )
    stroke_toast_subtype: Mapped[StrokeTOASTSubType] = mapped_column(
        Enum(StrokeTOASTSubType, name='subtype_toast_enum'),
        nullable=True,
    )
    stroke_hemo_subtype: Mapped[StrokeHemSubType] = mapped_column(
        Enum(StrokeHemSubType, name='subtype_hem_enum'),
        nullable=True,
    )
    medications: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    diary_entries: Mapped[list['DiaryEntry']] = relationship(
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='noload',
    )
    known_symptoms: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    doctor_id: Mapped[str] = mapped_column(
        String(DOC_ID_LEN),
        nullable=True,
    )
