from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.errors import DuplicateInfoError
from src.users.models import User


async def check_user_exists(user_id: int, session: AsyncSession) -> User:
    """Возвращает объект пользователя, если он уже существует в базе данных.

    В противном случае вызввает HTTPException с HTTPStatus.NOT_FOUND
    """
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Пользователь не найден',
        )
    return user


async def check_duplicate(
    username: str | None,
    email: str | None,
    phone: str | None,
    session: AsyncSession,
    exclude_id: UUID | None = None,
) -> None:
    """Проверяет, нет ли в базе данных пользователя с переданными данными."""
    checks = [
        (username, User.username, 'Имя пользователя занято.'),
        (email, User.email, 'Пользователь с таким email уже зарегистрирован.'),
        (
            phone,
            User.phone,
            'Пользователь с таким номером телефона уже зарегистрирован.',
        ),
    ]

    for value, column, message in checks:
        if value is None:
            continue

        query = select(User).where(column == value)
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)

        if await session.scalar(query):
            raise DuplicateInfoError(message)
