from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

import pytz
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.constants import DAY_NAMES
from src.db.session import AsyncSessionLocal
from src.reminders.models import PushSubscription, Reminder
from src.users.models import User

logger = logging.getLogger(__name__)


async def get_active_reminders_due_now() -> list[Reminder]:
    """Return all active reminders that are due at the current local time."""
    now_utc = datetime.now(tz=timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Reminder)
            .where(Reminder.is_active)
            .options(
                selectinload(Reminder.user).selectinload(
                    User.push_subscriptions,
                ),
            ),
        )
        reminders = result.scalars().all()
        logger.debug(
            'Fetched %s active reminder(s) from database',
            len(reminders),
        )

    due = []
    for reminder in reminders:
        logger.debug(
            'Evaluating reminder id=%s, time=%s', reminder.id, reminder.time,
        )

        if not reminder.time:
            logger.debug('Skipping reminder id=%s: no time set', reminder.id)
            continue

        tz = pytz.timezone(reminder.user.timezone)
        now_local = now_utc.astimezone(tz)
        if (
            reminder.time.hour != now_local.hour
            or reminder.time.minute != now_local.minute
        ):
            logger.debug(
                'Skipping reminder %s: scheduled=%02d:%02d, current=%02d:%02d',
                reminder.id,
                reminder.time.hour,
                reminder.time.minute,
                now_local.hour,
                now_local.minute,
            )
            continue

        current_day_local = DAY_NAMES[now_local.weekday()]
        if reminder.days and current_day_local not in reminder.days:
            logger.debug(
                'Skipping reminder %s: day "%s" not in scheduled days %s',
                reminder.id,
                current_day_local,
                reminder.days,
            )
            continue

        logger.debug('Reminder %s is due', reminder.id)
        due.append(reminder)

    logger.debug('%s reminder(s) due now', len(due))
    return due


async def delete_push_subscription_by_id(subscription_id: UUID) -> None:
    """Delete a push subscription by ID."""
    async with AsyncSessionLocal() as db:
        obj = await db.get(PushSubscription, subscription_id)
        if obj:
            await db.delete(obj)
            await db.commit()
            logger.info('Deleted push subscription %s', subscription_id)
        else:
            logger.warning(
                'Push subscription %s not found, skipping deletion',
                subscription_id,
            )


async def get_opted_in_users_with_subscriptions() -> list:
    """Return all active users with daily check-in enabled and push subs."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User)
            .where(User.is_active, User.daily_checkin_enabled)
            .options(selectinload(User.push_subscriptions)),
        )
        users = result.scalars().all()
        logger.debug(
            'Fetched %s opted-in user(s) with push subscriptions',
            len(users),
        )
        return users
