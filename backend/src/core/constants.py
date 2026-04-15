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


class StrokeTOASTSubType(StrEnum):
    """Ischenic stroke subtype."""

    LAA = 'large-artery atherosclerosis'
    CE = 'cardioembolism'
    LACUNAR = 'small-vessel occlusion'
    OTHERDETERM = 'stroke of other determined etiology'
    OTHERUNDETERM = 'stroke of undetermined etiology'


class StrokeHemSubType(StrEnum):
    """Hemorrhagic stroke subtype."""

    ICH = 'intracerebral hemorrhage'
    SAH = 'subarachnoid hemorrhage'


class Sex(StrEnum):
    """Patient sex."""

    M = 'male'
    F = 'female'
    UNKNOWN = 'unknown'


class EntryType(StrEnum):
    """Type of diary entry."""

    BP = 'blood_pressure'
    BLOOD_TEST = 'blood_test'
    MEDICATION = 'medication'
    SYMPTOM = 'symptom'


class AgeGroup(StrEnum):
    """Patient age group."""

    YOUNG = '18-44'
    MIDDLE = '45-65'
    OLD = '65+'


PHONE_LEN = 16
EMAIL_LEN = 254
PASSW_HASH_LEN = 256


JWT_LIFE = 3600
TOKEN_TYPE = 'Bearer'
TOKEN_FORMAT = 'JWT'
CREDENTIALS_EXCEPTIONS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail='Wrong credentials.',
)
ACCOUNT_INACTIVE_EXCEPTIONS = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail='Account deactivated.',
)
DOC_ID_LEN = 8
