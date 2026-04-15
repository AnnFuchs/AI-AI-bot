from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import (
    ACCOUNT_INACTIVE_EXCEPTIONS,
    CREDENTIALS_EXCEPTIONS,
    TOKEN_FORMAT,
    TOKEN_TYPE,
)
from src.db.session import get_async_session
from src.users.models import User

security = HTTPBearer(bearerFormat=TOKEN_FORMAT, scheme_name=TOKEN_TYPE)


async def get_current_user(
    session: AsyncSession = Depends(get_async_session),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current user."""
    token = credentials.credentials
    try:
        auth_data = settings.jwt_auth_data
        payload = jwt.decode(
            token,
            auth_data['secret_key'],
            algorithms=[auth_data['algorithm']],
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expired.',
        )
    except JWTError:
        raise CREDENTIALS_EXCEPTIONS

    sub = payload.get('sub')
    if not sub:
        raise CREDENTIALS_EXCEPTIONS

    user = await session.get(User, UUID(sub))
    if not user:
        raise CREDENTIALS_EXCEPTIONS
    if not user.is_active:
        raise ACCOUNT_INACTIVE_EXCEPTIONS

    return user


async def get_current_superuser(
    session: AsyncSession = Depends(get_async_session),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current cuperuser."""
    user = await get_current_user(session=session, credentials=credentials)
    if not user or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access forbidden.',
        )

    return user
