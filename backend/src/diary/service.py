from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import EntryType
from src.diary.models import DiaryEntry
from src.diary.schemas import DiaryEntryCreate


class DiaryEntryService:
    """C from CRUD for diary entry."""

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
        query = (
            select(DiaryEntry)
            .where(DiaryEntry.user_id == user_id)
            .order_by(DiaryEntry.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if entry_type is not None:
            query = query.where(DiaryEntry.entry_type == entry_type)
        result = await session.execute(query)
        return list(result.scalars().all())

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
        except IntegrityError:
            await session.rollback()
            raise ValueError(
                'Failed to create diary entry.'
                'Check user_id or data format.',
            )

        await session.refresh(entry)
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
        return result.scalar_one_or_none()

    async def delete_entry(
        self,
        entry: DiaryEntry,
        session: AsyncSession,
    ) -> None:
        """Delete a diary entry."""
        await session.delete(entry)
        await session.commit()


diary_service = DiaryEntryService()
