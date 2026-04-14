from datetime import datetime
from pathlib import Path as _Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pydantic import BaseModel as _BaseModel

from app.database import get_db
from app.models import DigestConfig, Keyword
from app.models.notification import Notification
from app.models.webhook import Webhook
from app.models.article import VALID_CATEGORIES
from app.schemas.article import (
    DigestConfigOut, DigestConfigUpdate,
    KeywordCreate, KeywordOut,
    NotificationOut,
    WebhookCreate, WebhookOut,
)
from app.services.auth import require_auth

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_auth)],
)


# ═══════════════════════════════════════════════════════════════════════════
# KEYWORDS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/keywords", response_model=list[KeywordOut])
def list_keywords(db: Session = Depends(get_db)):
    return db.query(Keyword).order_by(Keyword.keyword).all()


@router.post("/keywords", response_model=KeywordOut, status_code=201)
def create_keyword(body: KeywordCreate, db: Session = Depends(get_db)):
    existing = db.query(Keyword).filter(Keyword.keyword == body.keyword).first()
    if existing:
        raise HTTPException(409, f"Keyword '{body.keyword}' ya existe")
    kw = Keyword(keyword=body.keyword)
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


@router.patch("/keywords/{keyword_id}/toggle", response_model=KeywordOut)
def toggle_keyword(keyword_id: int, db: Session = Depends(get_db)):
    kw = db.query(Keyword).get(keyword_id)
    if not kw:
        raise HTTPException(404, "Keyword no encontrada")
    kw.is_active = not kw.is_active
    db.commit()
    db.refresh(kw)
    return kw


@router.delete("/keywords/{keyword_id}")
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    kw = db.query(Keyword).get(keyword_id)
    if not kw:
        raise HTTPException(404, "Keyword no encontrada")
    db.delete(kw)
    db.commit()
    return {"message": "Keyword eliminada"}


# ═══════════════════════════════════════════════════════════════════════════
# DIGEST CONFIG
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/digest/config", response_model=DigestConfigOut)
def get_digest_config(db: Session = Depends(get_db)):
    from app.config import settings
    cfg = db.query(DigestConfig).first()
    if not cfg:
        cfg = DigestConfig(hour=settings.digest_hour)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.patch("/digest/config", response_model=DigestConfigOut)
def update_digest_config(body: DigestConfigUpdate, db: Session = Depends(get_db)):
    from app.config import settings
    cfg = db.query(DigestConfig).first()
    if not cfg:
        cfg = DigestConfig(hour=settings.digest_hour)
        db.add(cfg)
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(cfg, field, val)
    cfg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cfg)
    if body.hour is not None:
        from app.scheduler.jobs import reschedule_digest
        reschedule_digest(cfg.hour)
    return cfg


# ═══════════════════════════════════════════════════════════════════════════
# WEBHOOKS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/webhooks", response_model=list[WebhookOut])
def list_webhooks(db: Session = Depends(get_db)):
    return db.query(Webhook).order_by(Webhook.created_at.desc()).all()


@router.post("/webhooks", response_model=WebhookOut, status_code=201)
def create_webhook(body: WebhookCreate, db: Session = Depends(get_db)):
    wh = Webhook(name=body.name, url=body.url, events=body.events, secret=body.secret)
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


@router.patch("/webhooks/{webhook_id}/toggle", response_model=WebhookOut)
def toggle_webhook(webhook_id: int, db: Session = Depends(get_db)):
    wh = db.query(Webhook).get(webhook_id)
    if not wh:
        raise HTTPException(404, "Webhook no encontrado")
    wh.is_active = not wh.is_active
    db.commit()
    db.refresh(wh)
    return wh


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    wh = db.query(Webhook).get(webhook_id)
    if not wh:
        raise HTTPException(404, "Webhook no encontrado")
    db.delete(wh)
    db.commit()
    return {"message": "Webhook eliminado"}


# ═══════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Notification)
    if unread_only:
        query = query.filter(Notification.read == False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.read == False).update({"read": True})
    db.commit()
    return {"message": "Todas marcadas como leídas"}


@router.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db)):
    n = db.query(Notification).get(notification_id)
    if not n:
        raise HTTPException(404, "Notificación no encontrada")
    n.read = True
    db.commit()
    return {"message": "Marcada como leída"}


@router.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    n = db.query(Notification).get(notification_id)
    if not n:
        raise HTTPException(404, "Notificación no encontrada")
    db.delete(n)
    db.commit()
    return {"message": "Notificación eliminada"}


@router.delete("/notifications")
def clear_all_notifications(db: Session = Depends(get_db)):
    db.query(Notification).delete()
    db.commit()
    return {"message": "Historial de notificaciones limpiado"}


# ═══════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/categories")
def get_categories():
    return {"categories": VALID_CATEGORIES}


# ═══════════════════════════════════════════════════════════════════════════
# RSS FEED OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import Request
from fastapi.responses import Response
from sqlalchemy.orm import joinedload
from app.models import Article


@router.get("/feed/rss")
def rss_feed(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    request: Request = None,
):
    articles = (
        db.query(Article)
        .options(joinedload(Article.summary), joinedload(Article.source))
        .filter(Article.status.in_(["approved", "sent"]))
        .order_by(Article.fetched_at.desc())
        .limit(limit)
        .all()
    )
    base_url = str(request.base_url).rstrip("/") if request else "http://localhost:8000"
    from app.services.rss_generator import generate_rss_feed
    xml_content = generate_rss_feed(articles, base_url)
    return Response(content=xml_content, media_type="application/rss+xml; charset=utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN SETTINGS — read/write .env from the panel
# ═══════════════════════════════════════════════════════════════════════════

_ENV_PATH = _Path(".env")

# Fields that are shown/editable from the panel (value is masked in GET if True)
_EDITABLE_FIELDS = {
    # key                     (label,                         masked, restart_needed)
    "AI_PROVIDER":            ("Proveedor IA",                False,  True),
    "GROQ_API_KEY":           ("Groq API Key",                True,   True),
    "GROQ_MODEL":             ("Groq Model",                  False,  True),
    "OPENAI_API_KEY":         ("OpenAI API Key",              True,   True),
    "OPENAI_MODEL":           ("OpenAI Model",                False,  True),
    "NEWSAPI_KEY":            ("NewsAPI Key",                 True,   True),
    "TELEGRAM_BOT_TOKEN":     ("Telegram Bot Token",          True,   True),
    "TELEGRAM_CHAT_ID":       ("Telegram Chat ID",            False,  True),
    "ADMIN_PASSWORD":         ("Contraseña del panel",        True,   True),
    "JWT_SECRET":             ("JWT Secret",                  True,   True),
    "JWT_EXPIRE_MINUTES":     ("Expiración JWT (minutos)",    False,  False),
    "SMTP_ENABLED":           ("Email habilitado",            False,  False),
    "SMTP_HOST":              ("SMTP Host",                   False,  True),
    "SMTP_PORT":              ("SMTP Puerto",                 False,  True),
    "SMTP_USER":              ("SMTP Usuario",                False,  True),
    "SMTP_PASSWORD":          ("SMTP Contraseña",             True,   True),
    "SMTP_FROM":              ("Email remitente",             False,  True),
    "SMTP_TO":                ("Email destinatario(s)",       False,  True),
    "FETCH_INTERVAL_MINUTES": ("Frecuencia fetch (minutos)",  False,  False),
    "DIGEST_HOUR":            ("Hora del digest (0-23)",      False,  False),
    "RELEVANCE_THRESHOLD":    ("Score mínimo auto-aprobar",   False,  False),
    "ENRICH_ARTICLES":        ("Enriquecer con IA",           False,  False),
    "SCRAPE_FULL_TEXT":       ("Scraping texto completo",     False,  False),
    "SOURCE_MAX_FAILURES":    ("Fallos antes de desactivar",  False,  False),
    "RATE_LIMIT_PER_MINUTE":  ("Rate limit (req/min)",        False,  False),
    "PANEL_PIN":              ("PIN del panel (alternativo)", True,   True),
}


def _read_env() -> dict[str, str]:
    """Parse .env into a dict of key→value."""
    result = {}
    if not _ENV_PATH.exists():
        return result
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _write_env(updates: dict[str, str]) -> None:
    """Write key=value pairs into .env, preserving comments and ordering."""
    if not _ENV_PATH.exists():
        content = ""
    else:
        content = _ENV_PATH.read_text(encoding="utf-8")

    lines = content.splitlines(keepends=True)
    updated_keys = set()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}\n")
                updated_keys.add(k)
                continue
        new_lines.append(line)

    # Append any keys that weren't already in the file
    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"\n{k}={v}\n")

    _ENV_PATH.write_text("".join(new_lines), encoding="utf-8")


@router.get("/admin/settings")
def get_admin_settings():
    """Read current .env settings (secrets are masked)."""
    env = _read_env()
    result = {}
    for key, (label, masked, restart) in _EDITABLE_FIELDS.items():
        raw_val = env.get(key, "")
        result[key] = {
            "label": label,
            "value": "••••••••" if (masked and raw_val) else raw_val,
            "masked": masked,
            "restart_needed": restart,
        }
    return {"settings": result}


class _SettingsUpdate(_BaseModel):
    updates: dict[str, str]


@router.post("/admin/settings")
def update_admin_settings(body: _SettingsUpdate):
    """Write settings to .env. Only whitelisted keys are accepted."""
    allowed = set(_EDITABLE_FIELDS.keys())
    rejected = [k for k in body.updates if k not in allowed]
    if rejected:
        raise HTTPException(400, f"Claves no permitidas: {rejected}")

    # Validate a few values
    for k, v in body.updates.items():
        if k in ("FETCH_INTERVAL_MINUTES", "DIGEST_HOUR", "RELEVANCE_THRESHOLD",
                 "SOURCE_MAX_FAILURES", "JWT_EXPIRE_MINUTES", "RATE_LIMIT_PER_MINUTE",
                 "SMTP_PORT"):
            if v and not v.lstrip("-").isdigit():
                raise HTTPException(400, f"{k} debe ser un número")

    _write_env(body.updates)
    needs_restart = any(
        _EDITABLE_FIELDS[k][2] for k in body.updates if k in _EDITABLE_FIELDS
    )
    return {
        "saved": list(body.updates.keys()),
        "restart_needed": needs_restart,
        "message": (
            "✅ Guardado. Reinicia el servidor para aplicar cambios marcados como 'requiere reinicio'."
            if needs_restart else "✅ Guardado."
        ),
    }
