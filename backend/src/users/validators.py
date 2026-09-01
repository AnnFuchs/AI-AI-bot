from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.errors import DuplicateInfoError
from src.users.models import User


async def check_user_exists(user_id: UUID, session: AsyncSession) -> User:
    """Return the user object if it already exists in the database.

    Raises HTTP 404 if not found.
    """
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found',
        )
    return user


async def check_duplicate(
    session: AsyncSession,
    phone: str | None = None,
    email: str | None = None,
    exclude_id: UUID | None = None,
) -> None:
    """Check there is no existing user with the given email or phone.

    Raises DuplicateInfoError if a conflict is found.
    """
    checks = [
        (email, User.email, 'User with this email already exists.'),
        (phone, User.phone, 'User with this phone number already exists.'),
    ]

    for value, column, message in checks:
        if value is None:
            continue

        query = select(User).where(column == value)
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)

        if await session.scalar(query):
            raise DuplicateInfoError(message)
