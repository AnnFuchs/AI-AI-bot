from datetime import datetime
from datetime import time as dt_time
from uuid import UUID

from pydantic import BaseModel


class ReminderOut(BaseModel):
    """Reminder schema."""

    id: UUID
    reminder_type: str
    med_name: str | None
    time: dt_time | None
    days: list = []
    is_active: bool
    created_at: datetime

    model_config = {'from_attributes': True}


class PushSubscriptionIn(BaseModel):
    """Push sub schema."""

    endpoint: str
    p256dh: str
    auth: str


class VapidPublicKeyOut(BaseModel):
    """VapidPubKey schema."""

    public_key: str
