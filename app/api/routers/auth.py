from fastapi import APIRouter, HTTPException
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
