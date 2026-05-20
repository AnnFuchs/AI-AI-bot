from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.db.session import get_async_session
from src.reminders.router_service import (
    deactivate_reminder,
    get_decoded_vapid_public_key,
    get_user_reminders,
    remove_push_subscription,
    upsert_push_subscription,
)
from src.reminders.schemas import (
    PushSubscriptionIn,
    ReminderOut,
    VapidPublicKeyOut,
)
from src.users.models import User

router = APIRouter(prefix='/reminders', tags=['Reminders'])


@router.get('/', response_model=list[ReminderOut])
async def get_reminders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[ReminderOut]:
    """Get reminders."""
    return await get_user_reminders(user.id, db)


@router.get('/vapid-public-key', response_model=VapidPublicKeyOut)
async def get_vapid_public_key() -> VapidPublicKeyOut:
    """Frontend needs this to subscribe to push notifications."""
    return VapidPublicKeyOut(public_key=get_decoded_vapid_public_key())


@router.post('/push-subscription', status_code=status.HTTP_201_CREATED)
async def save_push_subscription(
    payload: PushSubscriptionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Save or update browser push subscription."""
    await upsert_push_subscription(
        user.id, payload.endpoint, payload.p256dh, payload.auth, db,
    )
    return {'status': 'ok'}


@router.delete('/push-subscription', status_code=status.HTTP_204_NO_CONTENT)
async def delete_push_subscription(
    payload: PushSubscriptionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Call when user disables notifications."""
    await remove_push_subscription(user.id, payload.endpoint, db)


@router.delete('/{reminder_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete reminder."""
    reminder = await deactivate_reminder(reminder_id, user.id, db)
    if not reminder:
        raise HTTPException(status_code=404, detail='Reminder not found')
