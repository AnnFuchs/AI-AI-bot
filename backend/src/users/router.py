from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import (
    get_current_user,
    get_current_user_or_none,
    get_user_by_role,
)
from src.core.constants import Role
from src.db.session import get_async_session
from src.users.errors import DuplicateInfoError
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate, UserContext
from src.users.service import user_service
from src.users.validators import check_user_exists

router = APIRouter(prefix='/users', tags=['Пользователи'])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post(
    '',
    status_code=status.HTTP_201_CREATED,
    summary='New user creation',
)
async def create_user(
    user_in: UserCreate,
    session: SessionDep,
) -> None:
    """User creation endpoint."""
    try:
        return await user_service.create(user_in, session)
    except DuplicateInfoError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch(
    '/{user_id}',
    summary='Update user info',
)
async def update_user_info(
    user_id: UUID,
    update_data: UserUpdate,
    session: SessionDep,
) -> None:
    """User creation endpoint."""
    db_user = await check_user_exists(user_id, session)
    try:
        return await user_service.update(db_user, update_data, session)
    except DuplicateInfoError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# @router.get(
#     '/{user_id}',
#     summary='Get user context',
#     response_model=UserContext,
# )
# async def get_user_context(
#     user_id: UUID,
#     session: SessionDep,
# ) -> UserContext:
#     """Get user context for LLM."""
#     db_user = await check_user_exists(user_id, session)


# @router.post('/chat')
# async def chat():
#     POST ai-layer:8001/chat/stream (с UserContext)