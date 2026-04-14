"""
JWT authentication service.
Enabled only when ADMIN_PASSWORD is set in .env.
All tokens expire after JWT_EXPIRE_MINUTES (default 24h).

FastAPI dependency usage:
    from app.services.auth import require_auth
    @router.get("/protected", dependencies=[Depends(require_auth)])
    ...
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


def is_auth_enabled() -> bool:
    return bool(settings.admin_password)


def create_token(subject: str = "admin") -> str:
    try:
        from jose import jwt
    except ImportError:
        raise RuntimeError("python-jose not installed: pip install python-jose[cryptography]")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> dict | None:
    try:
        from jose import jwt
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except Exception:
        return None


def check_password(password: str) -> bool:
    return bool(settings.admin_password) and password == settings.admin_password


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency — validates Bearer JWT.
    If ADMIN_PASSWORD is not set, auth is disabled and all requests pass.
    Returns the decoded token payload (or empty dict when auth is disabled).
    """
    if not is_auth_enabled():
        return {}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
