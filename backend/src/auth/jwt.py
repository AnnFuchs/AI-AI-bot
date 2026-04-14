from datetime import datetime, timedelta, timezone

from jose import jwt

from src.core.config import settings
from src.core.constants import JWT_LIFE


def create_access_token(data: dict) -> str:
    """Генерация JWT токена."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(seconds=JWT_LIFE)
    to_encode.update({'exp': expire})
    auth_data = settings.jwt_auth_data
    return jwt.encode(
        to_encode,
        auth_data['secret_key'],
        algorithm=auth_data['algorithm'],
    )
