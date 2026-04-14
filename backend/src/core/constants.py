from enum import StrEnum

from fastapi import HTTPException, status


class Role(StrEnum):
    """Роль пользователя в системе."""

    PATIENT = 'patient'
    RELATIVE = 'relative'
    DOCTOR = 'doctor'
    ADMIN = 'admin'


JWT_LIFE = 3600
TOKEN_TYPE = 'Bearer'
CREDENTIALS_EXCEPTIONS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Wrong credentials.',
)
