from __future__ import annotations

import base64
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pywebpush import WebPushException, webpush

from src.core.config import settings
from src.core.logger import logger
from src.reminders.models import PushSubscription
from src.reminders.service import (
    delete_push_subscription_by_id,
    get_active_reminders_due_now,
)

scheduler = AsyncIOScheduler(timezone='UTC')


async def _send_push(
    subscription: PushSubscription,
    title: str,
    body: str,
) -> None:
    data = json.dumps({'title': title, 'body': body})
    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {
                    'p256dh': subscription.p256dh,
                    'auth': subscription.auth,
                },
            },
            data=data,
            vapid_private_key=base64.b64decode(
                settings.vapid_private_key.get_secret_value(),
            ).decode('utf-8'),
            vapid_claims={'sub': settings.vapid_claims_email},
        )
    except WebPushException as e:
        if e.response and e.response.status_code == 410:
            logger.info(
                'Push subscription expired, removing: %s', subscription.id,
            )
            await delete_push_subscription_by_id(subscription.id)
        else:
            logger.warning('Web push failed: %s', e)


async def check_reminders() -> None:
    """Fire push notifications for all due reminders."""
    reminders = await get_active_reminders_due_now()

    for reminder in reminders:
        if not reminder.user.push_subscriptions:
            continue

        if reminder.reminder_type == 'medication':
            title = 'Medication reminder'
            body = f"Time to take {reminder.med_name or 'your medication'}."
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
