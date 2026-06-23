from __future__ import annotations

import asyncio
import json
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pywebpush import WebPushException, webpush

from src.core.config import settings
from src.reminders.models import PushSubscription
from src.reminders.scheduler_service import (
    delete_push_subscription_by_id,
    get_active_reminders_due_now,
    get_opted_in_users_with_subscriptions,
)

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=settings.DEFAULT_TZ)


async def _send_push(
    subscription: PushSubscription,
    title: str,
    body: str,
) -> None:
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': {
                        'p256dh': subscription.p256dh,
                        'auth': subscription.auth,
                    },
                },
                data=json.dumps({'title': title, 'body': body}),
                vapid_private_key=(
                    settings.VAPID_PRIVATE_KEY.get_secret_value()
                ),
                vapid_claims={'sub': settings.VAPID_CLAIMS_EMAIL},
            ),
        )
        logger.debug('Push sent.')
    except WebPushException as e:
        if e.response and e.response.status_code == 410:
            logger.info(
                'Push subscription expired, removing: %s', subscription.id,
            )
            await delete_push_subscription_by_id(subscription.id)
        else:
            logger.warning('Web push failed: %s', e)
    except Exception as e:
        logger.warning('Web push failed: %s', e)


async def check_reminders() -> None:
    """Fire push notifications for all due reminders."""
    reminders = await get_active_reminders_due_now()

    for reminder in reminders:
        if not reminder.user.push_subscriptions:
            logger.debug(
                'Push subscription not found for user %s',
                reminder.user_id,
            )
            continue

        if reminder.reminder_type == 'medication':
            title = 'Оповещение о лекарстве'
            body = f"Время принять {reminder.med_name or 'ваше лекарство'}."
        else:
            title = 'Оповещение'
            body = f"Время для: {reminder.reminder_type}"

        for subscription in reminder.user.push_subscriptions:
            logger.debug('Ready to send push')
            await _send_push(subscription, title, body)


async def send_daily_checkins() -> None:
    """Send daily 'how is your day' push to all opted-in users."""
    users = await get_opted_in_users_with_subscriptions()

    for user in users:
        if not user.push_subscriptions:
            continue
        for subscription in user.push_subscriptions:
            await _send_push(
                subscription,
                title='How are you today?',
                body='Tap to log how you are feeling right now.',
            )


def start_scheduler() -> None:
    """Start scheduler."""
    scheduler.add_job(
        check_reminders,
        'interval',
        minutes=1,
        misfire_grace_time=5,
        id='check_reminders',
    )
    scheduler.add_job(
        send_daily_checkins,
        'cron',
        hour=10,
        minute=0,
        id='daily_checkins',
    )
    scheduler.start()


def stop_scheduler() -> None:
    """Stop scheduler."""
    scheduler.shutdown()
