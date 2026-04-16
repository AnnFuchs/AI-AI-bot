from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.constants import EntryType
from src.db.base import Base, CommonMixin

if TYPE_CHECKING:
    from src.users.models import User


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
