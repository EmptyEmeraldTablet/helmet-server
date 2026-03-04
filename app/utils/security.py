from datetime import datetime, timedelta
from secrets import token_urlsafe

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

def _build_schemes() -> list[str]:
    raw = settings.password_hash_scheme
    schemes = [item.strip() for item in raw.replace(",", " ").split() if item.strip()]
    # Ensure common schemes are available for backward-compatible verification.
    for fallback in ("bcrypt", "pbkdf2_sha256"):
        if fallback not in schemes:
            schemes.append(fallback)
    return schemes


pwd_context = CryptContext(schemes=_build_schemes(), deprecated="auto")
_fallback_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_secret(secret: str) -> str:
    try:
        return pwd_context.hash(secret)
    except Exception:
        # Fallback when bcrypt backend is unavailable or misconfigured.
        return _fallback_context.hash(secret)


def verify_secret(secret: str, hashed: str) -> bool:
    return pwd_context.verify(secret, hashed)


def generate_api_key() -> str:
    return token_urlsafe(32)


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    return payload.get("sub")
