import logging

from pydantic_extra_types.phone_numbers import PhoneNumber
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.password import get_password_hash
from src.users.errors import DuplicateInfoError, InactiveUserError
from src.users.models import User
from src.users.schemas import (
    AssignDoctorUpdate,
    UserCreate,
    UserUpdate,
)
from src.users.validators import check_duplicate

logger = logging.getLogger(__name__)


class UserService:
    """CRU from CRUD for User."""

    async def get_by_login(
        self,
        login: PhoneNumber,
        session: AsyncSession,
    ) -> User | None:
        """Get active user by phone number."""
        user = await session.scalar(
            select(User).where(
                User.phone == login,
            ),
        )
        if not user:
            logger.debug('User with login %s not found', login)
            return None

        if not user.is_active:
            logger.warning('User with login %s is inactive', login)
            return None

        logger.debug('Fetched user %s by login %s', user.id, login)
        return user

    async def create(self, data: UserCreate, session: AsyncSession) -> User:
        """Create user."""
        await check_duplicate(session=session, phone=data.phone)

        user_dict = data.model_dump()
        user_dict['hashed_password'] = get_password_hash(
            data.password.get_secret_value(),
        )
        user_dict.pop('password')

        user = User(**user_dict)
        session.add(user)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise DuplicateInfoError('User already exists.')

        await session.refresh(user)
        logger.debug('User %s created successfully', user.id)
        return user

    async def update(
        self,
        db_user: User,
        update_data: UserUpdate,
        session: AsyncSession,
    ) -> User:
        """Update user data."""
        await check_duplicate(
            session=session,
            email=update_data.email,
            phone=update_data.phone,
            exclude_id=db_user.id,
        )

        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(db_user, field, value)

        session.add(db_user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.warning(
                'Passed data %s for user %s update is incorrect',
                update_dict,
                db_user.id,
            )
            raise DuplicateInfoError('Passed data is incorrect.')

        await session.refresh(db_user)
        logger.debug('User %s updated successfully', db_user.id)
        return db_user

    async def assign_doctor(
        self,
        db_user: User,
        data: AssignDoctorUpdate,
        session: AsyncSession,
    ) -> User:
        """Assign or unassign a doctor to a patient."""
        db_user.doctor_id = data.doctor_id
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        logger.debug(
            'Doctor %s changed for user %s',
            db_user.doctor_id,
            db_user.id,
        )
        return db_user

    async def delete(self, db_user: User, session: AsyncSession) -> None:
        """Soft delete user by setting is_active to False."""
        if not db_user.is_active:
            logger.warning('User %s is already inactive', db_user.id)
            raise InactiveUserError('User is already deactivated.')

        db_user.is_active = False
        session.add(db_user)
        await session.commit()
        logger.debug('User %s successfully deactivated', db_user.id)


user_service = UserService()
