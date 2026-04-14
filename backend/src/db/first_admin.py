from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.users.errors import DuplicateInfoError
from src.users.schemas import AdminUserCreate
from src.users.service import user_service


async def create_first_admin(
    session: AsyncSession,
    login: str = settings.first_superuser_login,
    password: str = settings.first_superuser_password,
) -> None:
    """Автоматизация создания первого админа."""
    try:
        await user_service.create(
            AdminUserCreate(
                email=login,
                password=password,
            ),
            session,
        )
    except DuplicateInfoError as e:
        print(str(e))  # Здесь будет логирование
