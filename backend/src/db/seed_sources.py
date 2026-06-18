import logging

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.sources.data import SOURCES
from src.sources.errors import DuplicateInfoError
from src.sources.schemas import SourceCreate
from src.sources.service import source_service

logger = logging.getLogger(__name__)


async def seed_sources(session: AsyncSession) -> None:
    """Seed sources from constants on application startup."""
    for file_name, data in SOURCES.items():
        try:
            await source_service.create(
                SourceCreate(
                    source_file_name=file_name,
                    source_type=data['type'],
                    source_name=data['name'],
                    source_date=data.get('date'),
                    source_url=data.get('url'),
                ),
                session,
            )
            logger.info('Source "%s" created successfully.', file_name)
        except DuplicateInfoError as e:
            logger.info('Source "%s" already exists: %s', file_name, e)
        except ValidationError as e:
            logger.error('Source "%s" schema error: %s', file_name, e)
