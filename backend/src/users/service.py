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


class UserService:
    """CRU from CRUD for User."""

    async def get_by_login(
        self,
        login: str,
        session: AsyncSession,
    ) -> User | None:
        """Get active user by phone number."""
        return await session.scalar(
            select(User).where(
                User.phone == login,
                User.is_active == True,  # noqa: E712
            ),
        )

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
            raise DuplicateInfoError('User alredy exists.')

        await session.refresh(user)
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
            raise DuplicateInfoError('Passed data is incorrect.')

        await session.refresh(db_user)
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
        return db_user

    async def delete(self, db_user: User, session: AsyncSession) -> User:
        """Soft delete user by setting is_active to False."""
        if not db_user.is_active:
            raise InactiveUserError("User is already deactivated.")

        db_user.is_active = False
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        return db_user


user_service = UserService()
