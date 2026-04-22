import asyncio
import json
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import protected_routers, public_routers
from app.api.websocket import manager as ws_manager
from app.config import settings
from app.database import SessionLocal, create_tables, engine
from app.limiter import limiter
from app.models import Source
from app.scheduler.jobs import scheduler, start_scheduler

_bot_task: asyncio.Task | None = None


async def _bot_runner():
    """
    Run Telegram bot polling with automatic restart on crash.
    Backs off 5→10→30s on repeated failures to avoid hammering the API.
    """
    from app.services.telegram_bot import poll_updates
    backoff = 5
    while True:
        try:
            await poll_updates()
            backoff = 5  # reset after clean exit
        except asyncio.CancelledError:
            logger.info("Telegram bot runner cancelled")
            raise
        except Exception as e:
            logger.error(f"Telegram bot crashed ({type(e).__name__}: {e}). Restarting in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


def setup_logging():
    """Configure rotating file logger + console logger."""
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    fh = RotatingFileHandler(
        log_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def run_db_migrations():
    """
    Run safe column-addition migrations.
    - SQLite: uses PRAGMA table_info
    - PostgreSQL: uses information_schema
    create_all() handles new tables; this handles new columns on existing tables.
    """
    from app.models.article import Subscriber  # noqa — ensure all models imported
    from app.database import Base, _is_sqlite
    from sqlalchemy import text

    # Always create missing tables first
    Base.metadata.create_all(bind=engine)

    _article_cols = [
        ("sentiment",            "ALTER TABLE articles ADD COLUMN sentiment TEXT"),
        ("enrich_attempts",      "ALTER TABLE articles ADD COLUMN enrich_attempts INTEGER DEFAULT 0"),
        ("thumbnail_url",        "ALTER TABLE articles ADD COLUMN thumbnail_url TEXT"),
        ("cluster_id",           "ALTER TABLE articles ADD COLUMN cluster_id INTEGER"),
        ("feedback",             "ALTER TABLE articles ADD COLUMN feedback INTEGER DEFAULT 0"),
        ("is_recurring",         "ALTER TABLE articles ADD COLUMN is_recurring BOOLEAN DEFAULT FALSE"),
    ]
    _source_cols = [
        ("consecutive_failures", "ALTER TABLE sources ADD COLUMN consecutive_failures INTEGER DEFAULT 0"),
        ("last_error",           "ALTER TABLE sources ADD COLUMN last_error TEXT"),
        ("last_success_at",      "ALTER TABLE sources ADD COLUMN last_success_at TIMESTAMP"),
        ("disabled_at",          "ALTER TABLE sources ADD COLUMN disabled_at TIMESTAMP"),
    ]

    with engine.connect() as conn:
        if _is_sqlite:
            def existing(table):
                return [row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")]
            art_cols = existing("articles")
            src_cols = existing("sources")
        else:
            def existing(table):
                rows = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :t"
                ), {"t": table}).fetchall()
                return [r[0] for r in rows]
            art_cols = existing("articles")
            src_cols = existing("sources")

        for col, sql in _article_cols:
            if col not in art_cols:
                conn.execute(text(sql))
                logger.info(f"Migration: added articles.{col}")
        for col, sql in _source_cols:
            if col not in src_cols:
                conn.execute(text(sql))
                logger.info(f"Migration: added sources.{col}")

        # Summary structured fields
        _summary_cols_sql = [
            ("key_point",    "ALTER TABLE summaries ADD COLUMN key_point TEXT"),
            ("context_note", "ALTER TABLE summaries ADD COLUMN context_note TEXT"),
            ("impact",       "ALTER TABLE summaries ADD COLUMN impact TEXT"),
        ]
        sum_cols = existing("summaries")
        for col, sql in _summary_cols_sql:
            if col not in sum_cols:
                conn.execute(text(sql))
                logger.info(f"Migration: added summaries.{col}")

        conn.commit()


def seed_sources():
    """Seed default news sources if DB is empty."""
    db = SessionLocal()
    try:
        if db.query(Source).count() == 0:
            seeds_path = Path("seeds/default_sources.json")
            if seeds_path.exists():
                sources = json.loads(seeds_path.read_text(encoding="utf-8"))
                for s in sources:
                    db.add(Source(name=s["name"], source_type=s["source_type"], url=s["url"]))
                db.commit()
                logger.info(f"Seeded {len(sources)} default news sources")
    except Exception as e:
        logger.error(f"Seed error: {e}")
    finally:
        db.close()


# ─── PIN Protection Middleware ──────────────────────────────────────────────

_PIN_ENABLED = bool(getattr(settings, "panel_pin", None))
_PIN_VALUE   = getattr(settings, "panel_pin", "")

_BYPASS_PREFIXES = ("/api/", "/ws", "/feed/")


async def pin_middleware(request: Request, call_next):
    """
    Simple PIN gate for the web panel.
    API routes, WebSocket and RSS feed are always accessible.
    Web panel pages require X-Panel-Pin header or ?pin= query param.
    """
    if not _PIN_ENABLED:
        return await call_next(request)

    path = request.url.path
    # Always allow API, WS, and static assets
    if any(path.startswith(p) for p in _BYPASS_PREFIXES) or "." in path.split("/")[-1]:
        return await call_next(request)

    pin_from_header = request.headers.get("X-Panel-Pin", "")
    pin_from_query  = request.query_params.get("pin", "")
    if pin_from_header == _PIN_VALUE or pin_from_query == _PIN_VALUE:
        return await call_next(request)

    return JSONResponse(
        {"detail": "Panel protegido. Proporciona el PIN."},
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


# ─── Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_task

    setup_logging()
    logger.info("NewsLet v3.0 starting up...")

    create_tables()
    run_db_migrations()
    seed_sources()

    from app.services.startup_validator import validate_startup
    await validate_startup()

    start_scheduler()

    _token_ok = (
        settings.telegram_bot_token
        and settings.telegram_bot_token not in ("", "your-bot-token-here")
    )

    if _token_ok:
        webhook_url = getattr(settings, "webhook_base_url", "")
        if webhook_url:
            # Production (Render, etc.) — use webhooks, no background process needed
            from app.services.telegram_webhook import register_webhook
            ok = await register_webhook(webhook_url)
            if ok:
                logger.info(f"Telegram bot running via webhook → {webhook_url}")
            else:
                logger.warning("Webhook registration failed — bot may not respond")
        else:
            # Local dev — use polling
            _bot_task = asyncio.create_task(_bot_runner())
            logger.info("Telegram bot polling (local dev mode)")

    logger.info("NewsLet ready ✓")
    yield

    logger.info("NewsLet shutting down...")
    if _bot_task:
        _bot_task.cancel()
        try:
            await _bot_task
        except asyncio.CancelledError:
            pass
    scheduler.shutdown(wait=False)
    logger.info("Shutdown complete")


# ─── App ───────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NewsLet",
    description="Sistema profesional de agregación, análisis y distribución de noticias",
    version="3.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# PIN middleware (no-op if PANEL_PIN not set in .env)
app.middleware("http")(pin_middleware)

# Public routes (no auth) — registered BEFORE protected routes
for _r in public_routers:
    app.include_router(_r)
# Protected routes (JWT required when ADMIN_PASSWORD is set)
for _r in protected_routers:
    app.include_router(_r)


# ─── WebSocket endpoint ────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep alive — client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# Static web panel (must be last)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
