from passlib.context import CryptContext

password_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def get_password_hash(password: str) -> str:
    """Хэширование пароля."""
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Верификация пароля."""
    return password_context.verify(plain_password, hashed_password)
