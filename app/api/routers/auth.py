from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel as _BaseModel

from app.config import settings

public_router = APIRouter(prefix="/api/v1")


class _LoginBody(_BaseModel):
    password: str


# ═══════════════════════════════════════════════════════════════════════════
# AUTH (JWT — enabled only when ADMIN_PASSWORD is set)
# ═══════════════════════════════════════════════════════════════════════════

@public_router.post("/auth/login")
def auth_login(body: _LoginBody):
    from app.services.auth import check_password, create_token, is_auth_enabled
    if not is_auth_enabled():
        return {"token": None, "message": "Auth disabled — set ADMIN_PASSWORD in .env to enable"}
    if not check_password(body.password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    token = create_token()
    return {"token": token, "expires_in": f"{settings.jwt_expire_minutes}m"}


@public_router.get("/auth/status")
def auth_status():
    from app.services.auth import is_auth_enabled
    return {"auth_enabled": is_auth_enabled()}


@public_router.get("/auth/service-token")
def service_token(key: str):
    """
    Generate a long-lived JWT for GitHub Actions / cron callers.
    Protected by SERVICE_KEY env var instead of admin password.
    """
    from app.config import settings
    from app.services.auth import create_token
    svc_key = getattr(settings, "service_key", "")
    if not svc_key or key != svc_key:
        raise HTTPException(status_code=403, detail="Invalid service key")
    # 365-day token for automation
    from datetime import datetime, timedelta, timezone
    try:
        from jose import jwt
    except ImportError:
        raise HTTPException(500, "python-jose not installed")
    payload = {
        "sub": "service",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=365),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return {"token": token}


# ─── Telegram Webhook ──────────────────────────────────────────────────────
# Telegram calls this endpoint directly — must be public (no JWT)

@public_router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Receive Telegram updates via webhook (used in production on Render)."""
    try:
        update = await request.json()
        from app.services.telegram_bot import _process_update
        await _process_update(update)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Webhook error: {e}")
    # Always return 200 — Telegram retries on non-200
    return {"ok": True}
