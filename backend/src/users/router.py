from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_superuser, get_current_user
from src.db.session import get_async_session
from src.users.errors import DuplicateInfoError, InactiveUserError
from src.users.models import User
from src.users.schemas import (
    AssignDoctorUpdate,
    UserCreate,
    UserInfo,
    UserUpdate,
)
from src.users.service import user_service
from src.users.validators import check_user_exists

router = APIRouter(prefix='/users', tags=['Users'])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post(
    '/register',
    status_code=status.HTTP_201_CREATED,
    summary='New user creation',
)
async def create_user(
    user_in: UserCreate,
    session: SessionDep,
) -> None:
    """User creation endpoint."""
    try:
        await user_service.create(user_in, session)
    except DuplicateInfoError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    '/me',
    response_model=UserInfo,
    summary='Get current user info',
)
async def get_your_user_info(
    current_user: User = Depends(get_current_user),
) -> UserInfo:
    """Get current user info."""
    return current_user


@router.patch(
    '/me',
    response_model=UserInfo,
    summary='Update user info',
)
async def update_user_info(
    update_data: UserUpdate,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> UserInfo:
    """Update current user info."""
    try:
        return await user_service.update(current_user, update_data, session)
    except DuplicateInfoError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch(
    '/{user_id}/assign-doctor',
    response_model=UserInfo,
    summary='Assign or unassign a doctor to a patient',
)
async def assign_doctor(
    user_id: UUID,
    data: AssignDoctorUpdate,
    session: SessionDep,
    current_user: User = Depends(get_current_superuser),
) -> UserInfo:
    """Assign or unassign a doctor to a patient. Privileged endpoint."""
    db_user = await check_user_exists(user_id, session)
    return await user_service.assign_doctor(db_user, data, session)


@router.delete(
    '/me',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Deactivate current user',
)
async def deactivate_user(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft delete — sets is_active to False."""
    try:
        await user_service.delete(current_user, session)
    except InactiveUserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
