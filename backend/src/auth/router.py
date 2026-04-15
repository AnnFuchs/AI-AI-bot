from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import create_access_token
from src.auth.schemas import AuthData, AuthToken
from src.auth.service import auth_service
from src.core.constants import TOKEN_TYPE
from src.db.session import get_async_session

router = APIRouter(prefix='/auth', tags=['Аутентификация'])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post(
    '/login',
    summary='Get auth token',
    response_model=AuthToken,
)
async def auth_user(user_data: AuthData, session: SessionDep) -> AuthToken:
    """Return token for authentification."""
    user = await auth_service.auth_by_login(
        login=user_data.login,
        password=user_data.password,
        session=session,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Wrong login or password.',
        )

    access_token = create_access_token({'sub': str(user.id)})
    return AuthToken(access_token=access_token, token_type=TOKEN_TYPE)
