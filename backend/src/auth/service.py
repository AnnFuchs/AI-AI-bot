from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.password import verify_password
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
        if '@' in login:
            user = await session.scalar(
                select(User).where(User.email == login),
            )
        else:
            user = await session.scalar(
                select(User).where(User.phone == login),
            )

        if not user or not verify_password(
            plain_password=password.get_secret_value(),
            hashed_password=user.hashed_password,
        ):
            return None
        return user


auth_service = AuthService()
