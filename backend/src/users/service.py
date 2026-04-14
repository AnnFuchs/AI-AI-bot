from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.password import get_password_hash
from src.users.errors import DuplicateInfoError
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate
from src.users.validators import check_duplicate


class UserService:
    """Реализация CRUD для User."""

    async def get(self, user_id: UUID, session: AsyncSession) -> User | None:
        """Получение экземпляра пользователя по id."""
        return await session.get(User, user_id)

    async def get_all(self, session: AsyncSession) -> list[User] | None:
        """Получение всех пользователей."""
        db_users = await session.execute(select(User))
        return db_users.scalars().all()

    async def create(self, data: UserCreate, session: AsyncSession) -> User:
        """Создание пользователя."""
        await check_duplicate(
            username=data.username,
            email=data.email,
            phone=data.phone,
            session=session,
        )
        user_dict = data.model_dump()
        user_dict['hashed_password'] = get_password_hash(
            data.password.get_secret_value(),
        )
        user_dict.pop('password')

        user = User(**user_dict)

        session.add(user)
        try:
            await session.flush()
            await session.commit()
        except IntegrityError:
            raise DuplicateInfoError('Пользователь уже существует.')

        await session.refresh(user)
        return user

    async def update(
        self,
        db_user: User,
        update_data: UserUpdate,
        session: AsyncSession,
    ) -> User:
        """Обновление данных пользователя."""
        await check_duplicate(
            username=update_data.username,
            email=update_data.email,
            phone=update_data.phone,
            session=session,
            exclude_id=db_user.id,
        )

        update_dict = update_data.model_dump(exclude_unset=True)

        final_email = update_dict.get('email', db_user.email)
        final_phone = update_dict.get('phone', db_user.phone)
        if final_email is None and final_phone is None:
            raise ValueError(
                'У пользователя должен быть указан email или телефон.',
            )
        if 'password' in update_dict:
            secret = update_dict.pop('password')
            update_dict['hashed_password'] = get_password_hash(
                secret.get_secret_value(),
            )

        for field, value in update_dict.items():
            setattr(db_user, field, value)

        session.add(db_user)
        try:
            await session.flush()
            await session.commit()
        except IntegrityError:
            raise ValueError('Переданы неверные данные.')

        await session.refresh(db_user)
        return db_user


user_service = UserService()
