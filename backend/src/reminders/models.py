from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, CommonMixin

if TYPE_CHECKING:
    from src.users.models import User


class Reminder(CommonMixin, Base):
    """Reminder model."""

    __tablename__ = 'reminders'

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id'),
        nullable=False,
    )
    user: Mapped['User'] = relationship(back_populates='reminders')

    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False)
    med_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    days: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
    )
