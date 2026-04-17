from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.constants import SOURCE_NAME_LEN, SOURCE_URL_LEN, SourceType
from src.db.base import Base, CommonMixin


class Source(CommonMixin, Base):
    """Info source."""

    __tablename__ = 'sources'

    source_file_name: Mapped[str] = mapped_column(
        String(SOURCE_NAME_LEN),
        nullable=False,
        index=True,
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name='source_type_enum'),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(
        String(SOURCE_NAME_LEN),
        nullable=False,
    )
    source_date: Mapped[int] = mapped_column(
        Integer,
    )
    source_url: Mapped[str] = mapped_column(
        String(SOURCE_URL_LEN),
    )
