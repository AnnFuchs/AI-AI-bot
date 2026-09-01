from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.sources.errors import DuplicateInfoError
from src.sources.models import Source
from src.sources.schemas import SourceCreate
from src.sources.validators import check_source_duplicate


class SourceService:
    """Source service."""

    async def create(
        self, data: SourceCreate, session: AsyncSession,
    ) -> Source:
        """Create source."""
        await check_source_duplicate(
            session=session,
            source_file_name=data.source_file_name,
            source_name=data.source_name,
            source_url=data.source_url,
        )

        source = Source(**data.model_dump())
        session.add(source)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise DuplicateInfoError('Source already exists.')

        await session.refresh(source)
        return source


source_service = SourceService()
