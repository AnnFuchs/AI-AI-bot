from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.reminders.models import PushSubscription, Reminder

logger = logging.getLogger(__name__)


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
    reminders = list(result.scalars().all())
    logger.debug(
        'Retrieved %d reminders for user %s',
        len(reminders), user_id,
    )
    return reminders


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
        logger.debug('Reminder %s not found for user %s', reminder_id, user_id)
        return None
    if not reminder.is_active:
        logger.warning(
            'Reminder %s for user %s is already inactive',
            reminder_id,
            user_id,
        )
        return None
    reminder.is_active = False
    await db.commit()
    logger.info(
        'Reminder %s for user %s successfully deactivated',
        reminder_id,
        user_id,
    )
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
    logger.info('Push subscription upserted for user %s', user_id)


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
        logger.info(
            'Push subscription %s deleted for user %s',
            sub.id,
            user_id,
        )
    else:
        logger.warning('Push subscription not found for user %s', user_id)
