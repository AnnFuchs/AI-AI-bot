from __future__ import annotations

import base64
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.reminders.models import PushSubscription, Reminder


async def get_user_reminders(
    user_id: UUID, db: AsyncSession,
) -> list[Reminder]:
    """Get all active reminders for a user."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.user_id == user_id,
            Reminder.is_active,
        ),
    )
    return result.scalars().all()


async def deactivate_reminder(
    reminder_id: UUID, user_id: UUID, db: AsyncSession,
) -> Reminder | None:
    """Soft-delete a reminder. Returns None if not found."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == user_id,
        ),
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        return None
    reminder.is_active = False
    await db.commit()
    return reminder


async def upsert_push_subscription(
    user_id: UUID, endpoint: str, p256dh: str, auth: str, db: AsyncSession,
) -> None:
    """Save or update a push subscription."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        ),
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        db.add(PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        ))

    await db.commit()


async def remove_push_subscription(
    user_id: UUID, endpoint: str, db: AsyncSession,
) -> None:
    """Delete a push subscription by endpoint."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        ),
    )
    sub = result.scalar_one_or_none()
    if sub:
        await db.delete(sub)
        await db.commit()


def get_decoded_vapid_public_key() -> str:
    """Decode the base64-encoded VAPID public key."""
    return base64.b64decode(
        settings.vapid_public_key.get_secret_value(),
    ).decode('utf-8')
