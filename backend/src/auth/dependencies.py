import logging
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

logger = logging.getLogger(__name__)
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
            auth_data['SECRET_KEY'],
            algorithms=[auth_data['ALGORITHM']],
        )
    except ExpiredSignatureError:
        logger.warning('Expired token provided')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expired.',
        )
    except JWTError:
        logger.warning('Invalid JWT token provided')
        raise CREDENTIALS_EXCEPTIONS

    sub = payload.get('sub')
    if not sub:
        logger.warning('Token payload missing "sub" claim')
        raise CREDENTIALS_EXCEPTIONS

    try:
        user_id = UUID(sub)
    except ValueError:
        logger.warning('Token "sub" claim is not a valid UUID: %s', sub)
        raise CREDENTIALS_EXCEPTIONS

    user = await session.get(User, user_id)
    if not user:
        logger.warning('No user found for token sub: %s', user_id)
        raise CREDENTIALS_EXCEPTIONS
    if not user.is_active:
        logger.warning('Inactive user attempted access: %s', user_id)
        raise ACCOUNT_INACTIVE_EXCEPTIONS

    return user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access forbidden.',
        )

    return current_user
