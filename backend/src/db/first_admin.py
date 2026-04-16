from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logger import logger
from src.users.errors import DuplicateInfoError
from src.users.schemas import AdminUserCreate
from src.users.service import user_service


async def create_first_admin(
    session: AsyncSession,
    phone: str = settings.first_superuser_phone,
    password: str = settings.first_superuser_password.get_secret_value(),
) -> None:
    """Create the first superuser on application startup."""
    try:
        await user_service.create(
            AdminUserCreate(
                phone=phone,
                password=password,
            ),
            session,
        )
        logger.info('First admin created successfully.')
    except DuplicateInfoError as e:
        logger.info('First admin already exists: %s', e)
