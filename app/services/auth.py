"""
JWT authentication service.
Enabled only when ADMIN_PASSWORD is set in .env.
All tokens expire after JWT_EXPIRE_MINUTES (default 24h).
"""
from datetime import datetime, timedelta, timezone

from app.config import settings

_JWT_ENABLED = bool(settings.admin_password)


def is_auth_enabled() -> bool:
    return _JWT_ENABLED


def create_token(subject: str = "admin") -> str:
    """Create a signed JWT access token."""
    try:
        from jose import jwt
    except ImportError:
        raise RuntimeError("python-jose not installed. Run: pip install python-jose[cryptography]")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> dict | None:
    """Verify and decode a JWT token. Returns payload dict or None if invalid."""
    try:
        from jose import jwt, JWTError
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except Exception:
        return None


def check_password(password: str) -> bool:
    """Compare provided password against the configured admin password."""
    return bool(settings.admin_password) and password == settings.admin_password
