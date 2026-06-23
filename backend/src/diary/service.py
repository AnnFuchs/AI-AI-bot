import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import EntryType
from src.diary.models import DiaryEntry
from src.diary.schemas import DiaryEntryCreate

logger = logging.getLogger(__name__)


class DiaryEntryService:
    """CRD from CRUD for diary entry."""

    async def get_entries(
        self,
        user_id: UUID,
        session: AsyncSession,
        entry_type: EntryType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DiaryEntry]:
        """Get paginated diary entries for a use.

        Optionally filtered by type.
        """
        query = select(DiaryEntry).where(DiaryEntry.user_id == user_id)
        if entry_type is not None:
            query = query.where(DiaryEntry.entry_type == entry_type)
        query = (
            query
            .order_by(DiaryEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(query)
        entries = list(result.scalars().all())
        logger.debug(
            'Retrieved %d entries for user %s (type=%s, limit=%d, offset=%d)',
            len(entries), user_id, entry_type, limit, offset,
        )
        return entries

    async def create_entry(
        self, data: DiaryEntryCreate, user_id: UUID, session: AsyncSession,
    ) -> DiaryEntry:
        """Create diary entry."""
        entry_dict = data.model_dump()
        entry_dict['user_id'] = user_id

        entry = DiaryEntry(**entry_dict)
        session.add(entry)

        try:
            await session.commit()
        except IntegrityError as e:
            logger.warning(
                'Failed to create diary entry for user %s (type %s): %s',
                user_id,
                data.entry_type,
                e,
            )
            await session.rollback()
            raise ValueError(
                'Failed to create diary entry. '
                'Check user_id or data format.',
            )

        await session.refresh(entry)
        logger.info('Diary entry for user %s created successfully', user_id)
        return entry

    async def get_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
        session: AsyncSession,
    ) -> DiaryEntry | None:
        """Get a single diary entry belonging to the user."""
        result = await session.execute(
            select(DiaryEntry).where(
                DiaryEntry.id == entry_id,
                DiaryEntry.user_id == user_id,
            ),
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            logger.debug('Entry %s not found for user %s', entry_id, user_id)
        return entry

    async def delete_entry(
        self,
        entry: DiaryEntry,
        session: AsyncSession,
    ) -> None:
        """Delete a diary entry."""
        await session.delete(entry)
        await session.commit()
        logger.info(
            'Diary entry %s for user %s deleted successfully',
            entry.id, entry.user_id,
        )


diary_service = DiaryEntryService()
