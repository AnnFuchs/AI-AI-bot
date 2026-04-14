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
from src.users.responses import (
    USERS_CREATE_RESPONSES,
    USER_UPDATE_ME_RESPONSES,
)
from src.users.schemas import UserCreate, UserUpdate
from src.users.service import user_service
from src.users.validators import check_user_exists

router = APIRouter(prefix='/users', tags=['Пользователи'])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post(
    '',
    status_code=status.HTTP_201_CREATED,
    summary='New user registration',
    responses=USERS_CREATE_RESPONSES,
)
async def create_user(
    user_in: UserCreate,
    session: SessionDep,
    current_user: Annotated[
        User | None,
        Depends(get_current_user_or_none),
    ] = None,
) -> None:
    """_summary_.

    Args:
        user_in (UserCreate): _description_
        session (SessionDep): _description_
        current_user (Annotated[ User  |  None, Depends, optional): _description_. Defaults to None.

    Raises:
        HTTPException: _description_

    Returns:
        UserInfo: _description_

    """
    try:
        return await user_service.create(user_in, session)
    except DuplicateInfoError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
