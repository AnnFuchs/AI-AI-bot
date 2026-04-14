from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import create_access_token
from src.auth.responses import AUTH_LOGIN_RESPONSES
from src.auth.schemas import AuthData, AuthToken
from src.auth.service import auth_service
from src.core.constants import TOKEN_TYPE
from src.db.session import get_async_session

router = APIRouter(prefix='/auth', tags=['Аутентификация'])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]

@router.post(
    '/login',
    summary='Авторизация для swagger',
    response_model=AuthToken,
)
async def oauth_user(
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> AuthToken:
    """Возвращает токен для последующей авторизации пользователя."""
    check = await auth_service.auth_by_login(
        login=form_data.username,
        password=SecretStr(form_data.password),
        session=session,
    )
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Неверный логин или пароль',
        )

    access_token = create_access_token({'sub': str(check.id)})
    return AuthToken(access_token=access_token, token_type=TOKEN_TYPE)
