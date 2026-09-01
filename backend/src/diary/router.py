from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.core.constants import EntryType
from src.db.session import get_async_session
from src.diary.schemas import DiaryEntryInfo
from src.diary.service import diary_service
from src.users.models import User

router = APIRouter(prefix='/diary', tags=['Diary'])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.get(
    '',
    response_model=list[DiaryEntryInfo],
    summary='Get diary entries',
)
async def get_diary_entries(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    entry_type: EntryType | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[DiaryEntryInfo]:
    """Return paginated diary entries for the current user."""
    return await diary_service.get_entries(
        user_id=current_user.id,
        session=session,
        entry_type=entry_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    '/{entry_id}',
    response_model=DiaryEntryInfo,
    summary='Get a single diary entry',
)
async def get_diary_entry(
    entry_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> DiaryEntryInfo:
    """Return a single diary entry belonging to the current user."""
    entry = await diary_service.get_entry(entry_id, current_user.id, session)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Diary entry not found.',
        )
    return entry


@router.delete(
    '/{entry_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Delete a diary entry',
)
async def delete_diary_entry(
    entry_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a diary entry belonging to the current user."""
    entry = await diary_service.get_entry(entry_id, current_user.id, session)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Diary entry not found.',
        )
    await diary_service.delete_entry(entry, session)
