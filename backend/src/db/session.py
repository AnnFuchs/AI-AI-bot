import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

logger = logging.getLogger(__name__)
engine = create_async_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Generate aync session for db."""
    async with AsyncSessionLocal() as async_session:
        try:
            yield async_session
        except Exception:
            logger.error('Session generation failed.')
            await async_session.rollback()
            raise
