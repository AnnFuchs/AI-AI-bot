from __future__ import annotations

import json
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.core.constants import DAY_NAMES
from src.core.logger import logger
from src.db.session import AsyncSessionLocal
from src.reminders.models import PushSubscription, Reminder

scheduler = AsyncIOScheduler(timezone='UTC')


async def _send_push(
    subscription: PushSubscription,
    title: str, body: str,
) -> None:
    data = json.dumps({'title': title, 'body': body})
    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {
                    'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=data,
            vapid_private_key=settings.vapid_private_key.get_secret_value(),
            vapid_claims={'sub': settings.vapid_claims_email},
        )
    except WebPushException as e:
        if e.response and e.response.status_code == 410:
            logger.info(
                'Push subscription expired, removing: %s', subscription.id,
            )
            async with AsyncSessionLocal() as db:
                await db.delete(subscription)
                await db.commit()
        else:
            logger.warning('Web push failed: %s', e)


async def check_reminders() -> None:
    """Check are there reminders needed to be activated."""
    now = datetime.now(tz=timezone.utc)
    current_time = now.strftime('%H:%M')
    current_day = DAY_NAMES[now.weekday()]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Reminder)
            .where(
                Reminder.is_active,
                Reminder.time == current_time,
            )
            .options(
                selectinload(Reminder.user).selectinload(
                    __import__(
                        'src.users.models', fromlist=['User'],
                        ).User.push_subscriptions,
                ),
            ),
        )
        reminders = result.scalars().all()

        for reminder in reminders:
            if reminder.days and current_day not in reminder.days:
                continue

            if not reminder.user.push_subscriptions:
                continue

            if reminder.reminder_type == 'medication':
                title = 'Medication reminder'
                body = (
                    f"Time to take {reminder.med_name or 'your medication'}."
                )
            else:
                title = 'Reminder'
                body = f"Time for: {reminder.reminder_type}"

            for subscription in reminder.user.push_subscriptions:
                await _send_push(subscription, title, body)


def start_scheduler() -> None:
    """Start scheduler."""
    scheduler.add_job(
        check_reminders, 'interval', minutes=1, id='check_reminders',
    )
    scheduler.start()


def stop_scheduler() -> None:
    """Stop scheduler."""
    scheduler.shutdown()
