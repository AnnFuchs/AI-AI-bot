import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import RefreshToken
from src.auth.password import verify_password
from src.core.config import settings
from src.users.models import User
from src.users.service import user_service

logger = logging.getLogger(__name__)


class AuthService:
    """Auth service logic."""

    async def auth_by_login(
        self,
        login: str,
        password: SecretStr,
        session: AsyncSession,
    ) -> User | None:
        """User auth."""
        user = await user_service.get_by_login(login, session)

        if not user:
            logger.warning('Auth failed: user not found (login=%s)', login)
            return None

        if not verify_password(
            plain_password=password.get_secret_value(),
            hashed_password=user.hashed_password,
        ):
            logger.warning('Auth failed: invalid password (login=%s)', login)
            return None

        if not user.is_active:
            logger.warning('Auth failed: inactive account (login=%s)', login)
            return None

        return user

    async def save_refresh_token(
            self,
            user_id: UUID,
            jti: str,
            expires_at: datetime,
            session: AsyncSession,
    ) -> None:
        """Save refresh token."""
        token = RefreshToken(
            user_id=user_id,
            token_jti=jti,
            expires_at=expires_at,
        )
        session.add(token)
        await session.commit()

    async def revoke_refresh_token(
        self, jti: str, session: AsyncSession,
    ) -> None:
        """Revoke refresh token."""
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_jti == jti),
        )
        token = result.scalar_one_or_none()
        if token and not token.is_revoked:
            token.is_revoked = True
            await session.commit()

    async def get_valid_refresh_token(
        self, jti: str, session: AsyncSession,
    ) -> RefreshToken | None:
        """Get a non-revoked, non-expired refresh token record.

        Note: does not validate the associated user's active state;
        callers are responsible for that check.
        """
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_jti == jti,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            ),
        )
        return result.scalar_one_or_none()

    async def revoke_all_user_tokens(
        self, user_id: UUID | None, session: AsyncSession,
    ) -> None:
        """Revoke all active refresh tokens for a user (reuse detection?)."""
        if user_id is None:
            return
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            ),
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.is_revoked = True
        await session.commit()

    def extract_token_jti(self, token: str) -> str:
        """Decode token, enforce expiry, and extract JTI claim."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_auth_data['SECRET_KEY'],
                algorithms=[settings.jwt_auth_data['ALGORITHM']],
            )
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Refresh token expired.',
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid refresh token.',
            )

        jti = payload.get('jti')
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid refresh token: missing JTI.',
            )
        return jti

    def extract_jti_safe(self, token: str) -> str | None:
        """Safely decode token ignoring expiry and return JTI or None.

        Used during logout where an expired refresh token should still
        be revoked rather than silently ignored.
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_auth_data['SECRET_KEY'],
                algorithms=[settings.jwt_auth_data['ALGORITHM']],
                options={"verify_exp": False},
            )
            return payload.get('jti')
        except JWTError:
            return None

    def extract_user_id_safe(self, token: str) -> UUID | None:
        """Safely decode token ignoring expiry and return user UUID or None."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_auth_data['SECRET_KEY'],
                algorithms=[settings.jwt_auth_data['ALGORITHM']],
                options={"verify_exp": False},
            )
            sub = payload.get('sub')
            return UUID(sub) if sub else None
        except (JWTError, ValueError):
            return None


auth_service = AuthService()
