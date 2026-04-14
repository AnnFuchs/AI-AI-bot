from datetime import date
from uuid import UUID

from sqlalchemy import JSON, Boolean, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import (
    EMAIL_LEN,
    PASSW_HASH_LEN,
    PHONE_LEN,
    EntryType,
    Role,
    Sex,
    StrokeHemSubType,
    StrokeTOASTSubType,
    StrokeType,
)
from src.db.base import Base, CommonMixin


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
    )
    hashed_password: Mapped[str] = mapped_column(
        String(PASSW_HASH_LEN),
        nullable=False,
    )
    date_of_birth: Mapped[date] = mapped_column(
        Date,
    )
    sex: Mapped[Sex] = mapped_column(
        Enum(Sex, name='sex_enum'),
        default=Sex.UNKNOWN,
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
    )
    stroke_hemo_subtype: Mapped[StrokeHemSubType] = mapped_column(
        Enum(StrokeHemSubType, name='subtype_hem_enum'),
    )
    medications: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    diary_entries: Mapped[list["DiaryEntry"]] = relationship(
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='selectin',
    )
    known_symptoms: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )


class DiaryEntry(CommonMixin, Base):
    """Single patient log entry."""

    __tablename__ = 'diary_entries'

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id'),
        nullable=False,
    )
    user: Mapped['User'] = relationship(back_populates='diary_entries')
    entry_type: Mapped[EntryType] = mapped_column(
        Enum(EntryType, name='entry_type_enum'),
        nullable=False,
        index=True,
    )
    entry_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
