from __future__ import annotations

import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.core.config import settings
from src.db.session import get_async_session
from src.reminders.models import PushSubscription, Reminder
from src.reminders.schemas import (
    PushSubscriptionIn,
    ReminderOut,
    VapidPublicKeyOut,
)
from src.users.models import User

router = APIRouter(prefix='/reminders', tags=['reminders'])


@router.get('/', response_model=list[ReminderOut])
async def get_reminders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[Reminder]:
    """Get reminders."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.user_id == user.id, Reminder.is_active,
        ),
    )
    return result.scalars().all()


@router.delete('/{reminder_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Felete reminder."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id, Reminder.user_id == user.id,
        ),
    )
    reminder = result.scalar_one_or_none()
    if not reminder:
        raise HTTPException(status_code=404, detail='Reminder not found')
    reminder.is_active = False
    await db.commit()


@router.get('/vapid-public-key', response_model=VapidPublicKeyOut)
async def get_vapid_public_key() -> VapidPublicKeyOut:
    """Frontend needs this to subscribe to push notifications."""
    return VapidPublicKeyOut(
        public_key=base64.b64decode(
            settings.vapid_public_key.get_secret_value(),
        ).decode('utf-8'),
    )


@router.post('/push-subscription', status_code=status.HTTP_201_CREATED)
async def save_push_subscription(
    payload: PushSubscriptionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Save or update browser push subscription."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == user.id,
            PushSubscription.endpoint == payload.endpoint,
        ),
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.p256dh = payload.p256dh
        existing.auth = payload.auth
    else:
        db.add(PushSubscription(
            user_id=user.id,
            endpoint=payload.endpoint,
            p256dh=payload.p256dh,
            auth=payload.auth,
        ))

    await db.commit()
    return {'status': 'ok'}


@router.delete('/push-subscription', status_code=status.HTTP_204_NO_CONTENT)
async def remove_push_subscription(
    payload: PushSubscriptionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Call when user disables notifications."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == user.id,
            PushSubscription.endpoint == payload.endpoint,
        ),
    )
    sub = result.scalar_one_or_none()
    if sub:
        await db.delete(sub)
        await db.commit()
