from enum import StrEnum

from fastapi import HTTPException, status


class Role(StrEnum):
    """User role."""

    PATIENT = 'patient'
    RELATIVE = 'relative'
    DOCTOR = 'doctor'
    ADMIN = 'admin'


class StrokeType(StrEnum):
    """Type of stroke."""

    ISCHEMIC = 'ischemic'
    HEMORRHAGIC = 'hemorrhagic'
    UNKNOWN = 'unknown'


class Sex(StrEnum):
    """Patient sex."""

    M = 'male'
    F = 'female'
    UNKNOWN = 'unknown'


class EntryType(StrEnum):
    """Type of dieary entry."""

    BP = 'blood_pressure'
    BLOOD_TEST = 'blood_test'
    MEDICATION = 'medication'


PHONE_LEN = 16
EMAIL_LEN = 254
PASSW_HASH_LEN = 256


JWT_LIFE = 3600
TOKEN_TYPE = 'Bearer'
CREDENTIALS_EXCEPTIONS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Wrong credentials.',
)
