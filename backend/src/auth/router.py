from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.jwt import create_access_token, create_refresh_token
from src.auth.schemas import AuthData, AuthToken, RefreshTokenRequest
from src.auth.service import auth_service
from src.core.constants import REFRESH_TOKEN_LIFE, TOKEN_TYPE
from src.db.session import get_async_session
from src.users.models import User

router = APIRouter(prefix='/auth', tags=['Аутентификация'])

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


@router.post('/login', summary='Get auth token', response_model=AuthToken)
async def auth_user(user_data: AuthData, session: SessionDep) -> AuthToken:
    """Return access and refresh tokens."""
    user = await auth_service.auth_by_login(
        user_data.login, user_data.password, session,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Wrong login or password.',
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Account is inactive.',
        )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token_str, jti = create_refresh_token({"sub": str(user.id)})
    await auth_service.save_refresh_token(
        user.id,
        jti,
        datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_LIFE),
        session,
    )
    return AuthToken(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type=TOKEN_TYPE,
    )


@router.post(
    '/refresh',
    summary='Refresh auth token',
    response_model=AuthToken,
)
async def refresh_token(
    payload: RefreshTokenRequest,
    session: SessionDep,
) -> AuthToken:
    """Rotate refresh token and issue new access token."""
    jti = auth_service.extract_token_jti(payload.refresh_token)

    db_token = await auth_service.get_valid_refresh_token(jti, session)
    if not db_token:
        await auth_service.revoke_all_user_tokens(
            auth_service.extract_user_id_safe(payload.refresh_token), session,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token revoked or expired.',
        )

    user = await session.get(User, db_token.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found or inactive.',
        )

    await auth_service.revoke_refresh_token(jti, session)

    new_access = create_access_token({"sub": str(user.id)})
    new_refresh_str, new_jti = create_refresh_token({"sub": str(user.id)})
    await auth_service.save_refresh_token(
        user.id,
        new_jti,
        datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_LIFE),
        session,
    )
    return AuthToken(
        access_token=new_access,
        refresh_token=new_refresh_str,
        token_type=TOKEN_TYPE,
    )


@router.post('/logout', summary='Log user out')
async def logout_user(
    payload: RefreshTokenRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Revoke refresh token."""
    jti = auth_service.extract_jti_safe(payload.refresh_token)
    if jti:
        await auth_service.revoke_refresh_token(jti, session)
    return {'detail': 'Successfully logged out.'}
