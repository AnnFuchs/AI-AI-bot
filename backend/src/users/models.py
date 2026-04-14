from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.constants import Role
from src.db.base import Base


class User(Base):
    """Класс пользователя.

    Аттрибуты:
        id - UUID, унаследовано из класса Base
        email - str
        phone - str| None
        hashed_password - str
        is_active - bool
        role - Role(StrEnum)
        created_at - datetime, унаследовано из класса Base
        updated_at - datetime, унаследовано из класса Base
        is_active - bool, унаследовано из класса Base
    """

    __tablename__ = 'users'

    email: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        index=True,
    )
    phone: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    role: Mapped[Role] = mapped_column(
        Enum(Role, name='role_enum'),
        default=Role.USER,
        nullable=False,
    )

    is_superuser