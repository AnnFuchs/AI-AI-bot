from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.constants import (
    SOURCE_NAME_LEN,
    SOURCE_URL_LEN,
    SOURCE_YEAR_START,
    SourceType,
)


class SourceCreate(BaseModel):
    """Pydantic-schema for source entry creation."""

    source_type: SourceType
    source_name: str = Field(max_length=SOURCE_NAME_LEN)
    source_date: int | None = Field(default=None, gt=SOURCE_YEAR_START)
    source_url: str | None = Field(default=None, max_length=SOURCE_URL_LEN)
    source_file_name: str = Field(max_length=SOURCE_NAME_LEN)

    @field_validator('source_date')
    @classmethod
    def validate_source_date(cls, v: int | None) -> int | None:
        """Check if source year is greater or equal to the next year."""
        if v is None:
            return v
        if v >= datetime.today().year + 1:
            raise ValueError(
                f'source_date must be less than {datetime.today().year + 1}',
            )
        return v

    model_config = ConfigDict(extra='forbid')


class SourceInfo(SourceCreate):
    """Source entry response schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
