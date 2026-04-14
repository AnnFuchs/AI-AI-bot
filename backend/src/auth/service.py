from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.password import verify_password
from src.core.logger import logger
from src.users.models import User


class AuthService:
    """Сервис-класс для аутентификации."""

    async def auth_by_login(
        self,
        login: str,
        password: SecretStr,
        session: AsyncSession,
    ) -> User | None:
        """Аутентификация пользователей."""
        user = await session.scalar(
                select(User).where(User.phone == login),
            )

        if not user:
            logger.warning("Auth failed: user not found (login=%s)", login)
            return None

        if not verify_password(
            plain_password=password.get_secret_value(),
            hashed_password=user.hashed_password,
        ):
            logger.warning("Auth failed: invalid password (login=%s)", login)
            return None

        if not user.is_active:
            logger.warning("Auth failed: inactive account (login=%s)", login)
            return None

        return user


auth_service = AuthService()
