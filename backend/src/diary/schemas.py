from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.core.constants import EntryType


class DiaryEntryCreate(BaseModel):
    """Pydantic-schema for dairy entry creation."""

    entry_type: EntryType
    entry_json: dict[str, Any]

    model_config = ConfigDict(extra='forbid')


class DiaryEntryInfo(BaseModel):
    """Diary entry response schema."""

    id: UUID
    user_id: UUID
    entry_type: EntryType
    entry_json: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
