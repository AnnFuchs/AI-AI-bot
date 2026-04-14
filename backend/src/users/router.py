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
    USERS_LIST_RESPONSES,
    USER_GET_BY_ID_RESPONSES,
    USER_GET_ME_RESPONSES,
    USER_UPDATE_BY_ID_RESPONSES,
    USER_UPDATE_ME_RESPONSES,
)
from src.users.schemas import UserCreate, UserInfo, UserUpdate
from src.users.service import user_service
from src.users.validators import check_user_exists

router = APIRouter(prefix='/users', tags=['Пользователи'])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.get(
    '',
    response_model=list[UserInfo],
    summary='Получение списка пользователей',
    dependencies=[Depends(get_user_by_role([Role.ADMIN, Role.MANAGER]))],
    responses=USERS_LIST_RESPONSES,
)
async def get_all_users(session: SessionDep) -> list[UserInfo]:
    """Возвращает информацию о всех пользователях.

    Только для администраторов или менеджеров
    """
    return await user_service.get_all(session)


@router.post(
    '',
    response_model=UserInfo,
    status_code=status.HTTP_201_CREATED,
    summary='Регистрация нового пользователя',
    responses=USERS_CREATE_RESPONSES,
)
async def create_user(
    user_in: UserCreate,
    session: SessionDep,
    current_user: Annotated[
        User | None,
        Depends(get_current_user_or_none),
    ] = None,
) -> UserInfo:
    """Создает нового пользователя с указанными данными.

    Регистрировать пользователя может или не авторизированный пользователь
    или менеджер или администратор.
    Обязательные поля:
    - username
    - password
    - email или phone
    """
    if current_user and current_user.role not in {Role.MANAGER, Role.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Недостаточно прав',
        )

    try:
        return await user_service.create(user_in, session)
    except DuplicateInfoError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    '/me',
    response_model=UserInfo,
    summary='Получение информации о текущем пользователе',
    responses=USER_GET_ME_RESPONSES,
)
async def get_your_user_info(
    current_user: User = Depends(get_current_user),
) -> UserInfo:
    """Возвращает информацию о текущем пользователе.

    Только для авторизированных пользователей
    """
    return current_user


@router.patch(
    '/me',
    response_model=UserInfo,
    summary='Обновление информации о текущем пользователе',
    responses=USER_UPDATE_ME_RESPONSES,
)
async def update_your_user_info(
    update_data: UserUpdate,
    session: SessionDep,
    user: User = Depends(get_current_user),
) -> UserInfo:
    """Возвращает обновленную информацию о пользователе.

    Только для авторизированных пользователей
    """
    try:
        return await user_service.update(
            db_user=user,
            update_data=update_data,
            session=session,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    '/{user_id}',
    response_model=UserInfo,
    summary='Получение информации о пользователе по его id',
    dependencies=[Depends(get_user_by_role([Role.ADMIN, Role.MANAGER]))],
    responses=USER_GET_BY_ID_RESPONSES,
)
async def get_user_by_id(user_id: UUID, session: SessionDep) -> UserInfo:
    """Возвращает информацию о пользователе по его ID.

    Только для администраторов или менеджеров
    """
    return await user_service.get(user_id, session)


@router.patch(
    '/{user_id}',
    response_model=UserInfo,
    summary='Обновление информации о пользователе по его id',
    dependencies=[Depends(get_user_by_role([Role.ADMIN, Role.MANAGER]))],
    responses=USER_UPDATE_BY_ID_RESPONSES,
)
async def update_user_by_id(
    user_id: UUID,
    update_data: UserUpdate,
    session: SessionDep,
) -> UserInfo:
    """Возвращает обновленную информацию о пользователе по его ID.

    Только для администраторов или менеджеров
    """
    db_user = await check_user_exists(user_id=user_id, session=session)
    try:
        return await user_service.update(
            db_user=db_user,
            update_data=update_data,
            session=session,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
