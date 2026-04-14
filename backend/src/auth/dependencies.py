from typing import Annotated, Callable, Sequence
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import CREDENTIALS_EXCEPTIONS, Role
from src.db.session import get_async_session
from src.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/v1/auth/oauth/login')
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl='api/v1/auth/oauth/login',
    auto_error=False,
)


async def get_current_user(
    session: AsyncSession = Depends(get_async_session),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Получение текущего пользователя."""
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
            detail='Токен истек.',
        )
    except JWTError:
        raise CREDENTIALS_EXCEPTIONS

    sub = payload.get('sub')
    if not sub:
        raise CREDENTIALS_EXCEPTIONS

    user_id = UUID(sub)
    user = await session.get(User, user_id)
    if not user:
        raise CREDENTIALS_EXCEPTIONS

    return user


async def get_current_user_or_none(
    session: AsyncSession = Depends(get_async_session),
    token: str = Depends(oauth2_scheme_optional),
) -> User:
    """Получение текущего пользователя, если токен валидный, иначе None."""
    if token is None:
        return None

    try:
        auth_data = settings.jwt_auth_data
        payload = jwt.decode(
            token,
            auth_data['secret_key'],
            algorithms=[auth_data['algorithm']],
        )
    except (ExpiredSignatureError, JWTError):
        return None

    sub = payload.get('sub')
    if not sub:
        return None

    user_id = UUID(sub)
    return await session.get(User, user_id)


def get_user_by_role(required_roles: Sequence[Role]) -> Callable:
    """Фабрика зависимости для проверки роли пользователя."""

    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Недостаточно прав для выполнения операции',
            )
        return current_user

    return role_checker
