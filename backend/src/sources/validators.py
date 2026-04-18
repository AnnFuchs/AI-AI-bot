from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.sources.errors import DuplicateInfoError
from src.sources.models import Source


async def check_source_duplicate(
    session: AsyncSession,
    source_file_name: str | None = None,
    source_name: str | None = None,
    source_url: str | None = None,
    exclude_id: UUID | None = None,
) -> None:
    """Check there is no existing source with the given unique fields.

    Raises DuplicateInfoError if a conflict is found.
    """
    checks = [
        (
            source_file_name,
            Source.source_file_name,
            'Source with this file name already exists.',
        ),
        (
            source_name,
            Source.source_name,
            'Source with this name already exists.',
        ),
        (
            source_url,
            Source.source_url,
            'Source with this URL already exists.',
        ),
    ]

    for value, column, message in checks:
        if value is None:
            continue

        query = select(Source).where(column == value)
        if exclude_id is not None:
            query = query.where(Source.id != exclude_id)

        if await session.scalar(query):
            raise DuplicateInfoError(message)
