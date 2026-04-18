from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt

from src.core.config import settings
from src.core.constants import JWT_LIFE, REFRESH_TOKEN_LIFE


def create_access_token(data: dict) -> str:
    """Generate JWT token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(seconds=JWT_LIFE)
    to_encode.update({'exp': expire})
    auth_data = settings.jwt_auth_data
    return jwt.encode(
        to_encode,
        auth_data['SECRET_KEY'],
        algorithm=auth_data['ALGORITHM'],
    )


def create_refresh_token(data: dict) -> tuple[str, str]:
    """Generate refresh token and return (token, jti)."""
    to_encode = data.copy()
    jti = str(uuid4())
    expire = datetime.now(timezone.utc) + timedelta(seconds=REFRESH_TOKEN_LIFE)
    to_encode.update({'exp': expire, 'jti': jti, 'type': 'refresh'})
    auth_data = settings.jwt_auth_data
    return jwt.encode(
        to_encode,
        auth_data['SECRET_KEY'],
        algorithm=auth_data['ALGORITHM']), jti
