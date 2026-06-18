import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.users.errors import DuplicateInfoError
from src.users.schemas import AdminUserCreate
from src.users.service import user_service

logger = logging.getLogger(__name__)


async def create_first_admin(
    session: AsyncSession,
    phone: str = settings.FIRST_SUPERUSER_PHONE,
    password: str = settings.FIRST_SUPERUSER_PASSWORD.get_secret_value(),
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
