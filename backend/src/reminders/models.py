from __future__ import annotations

from datetime import time as dt_time
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, CommonMixin

if TYPE_CHECKING:
    from src.users.models import User


class Reminder(CommonMixin, Base):
    """Reminder model."""

    __tablename__ = 'reminders'

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id'), nullable=False,
    )
    user: Mapped['User'] = relationship(back_populates='reminders')

    reminder_type: Mapped[str] = mapped_column(String(50), nullable=False)
    med_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    time: Mapped[dt_time | None] = mapped_column(
        Time(timezone=True), nullable=True,
    )
    days: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class PushSubscription(CommonMixin, Base):
    """Browser Web Push subscription."""

    __tablename__ = 'push_subscriptions'

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id'), nullable=False,
    )
    user: Mapped['User'] = relationship(back_populates='push_subscriptions')

    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(512), nullable=False)
    auth: Mapped[str] = mapped_column(String(256), nullable=False)
