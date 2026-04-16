from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytz
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.constants import DAY_NAMES
from src.db.session import AsyncSessionLocal
from src.reminders.models import PushSubscription, Reminder


async def get_active_reminders_due_now() -> list[Reminder]:
    """Return all active reminders that are due at the current local time."""
    now_utc = datetime.now(tz=timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Reminder)
            .where(Reminder.is_active)
            .options(
                selectinload(Reminder.user).selectinload(
                    __import__(
                        'src.users.models', fromlist=['User'],
                    ).User.push_subscriptions,
                ),
            ),
        )
        reminders = result.scalars().all()

    due = []
    for reminder in reminders:
        if not reminder.time:
            continue

        tz = pytz.timezone(reminder.user.timezone)
        now_local = now_utc.astimezone(tz)
        current_time_local = now_local.replace(
            second=0, microsecond=0,
        ).timetz()
        current_day_local = DAY_NAMES[now_local.weekday()]

        if reminder.time != current_time_local:
            continue
        if reminder.days and current_day_local not in reminder.days:
            continue

        due.append(reminder)

    return due


async def delete_push_subscription_by_id(subscription_id: UUID) -> None:
    """Delete a push subscription by ID."""
    async with AsyncSessionLocal() as db:
        obj = await db.get(PushSubscription, subscription_id)
        if obj:
            await db.delete(obj)
            await db.commit()
