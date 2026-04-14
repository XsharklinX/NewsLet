import asyncio
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models import Article, DigestConfig

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


_FETCH_TIMEOUT = 5 * 60  # 5 minutes max per full fetch cycle


async def job_fetch_all():
    """
    Full fetch pipeline with a 5-minute hard timeout to avoid hanging forever.
    1. Parallel fetch from all sources (each source has its own httpx timeout)
    2. Keyword alerts on new articles
    3. Auto-summarize new articles immediately
    4. Broadcast live update via WebSocket
    5. Push in-app notification
    """
    logger.info("Scheduler: starting fetch cycle")
    try:
        await asyncio.wait_for(_fetch_all_impl(), timeout=_FETCH_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error(f"Scheduler: fetch cycle timed out after {_FETCH_TIMEOUT}s")


async def _fetch_all_impl():
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=settings.fetch_interval_minutes + 2)

        from app.services.rss_fetcher import fetch_all_rss
        from app.services.newsapi_fetcher import fetch_all_newsapi
        from app.services.web_scraper import fetch_all_scrapers

        # Run all fetchers in parallel (each uses its own httpx client with timeouts)
        rss, newsapi, scraped = await asyncio.gather(
            fetch_all_rss(db),
            fetch_all_newsapi(db),
            fetch_all_scrapers(db),
            return_exceptions=True,
        )
        # Handle exceptions from gather
        rss     = rss     if isinstance(rss,     int) else 0
        newsapi = newsapi if isinstance(newsapi, int) else 0
        scraped = scraped if isinstance(scraped, int) else 0
        total   = rss + newsapi + scraped

        logger.info(f"Scheduler: fetched {total} new articles (rss={rss} newsapi={newsapi} scraper={scraped})")

        if total > 0:
            new_articles = db.query(Article).filter(Article.fetched_at >= cutoff).all()

            # Keyword alerts
            from app.services.keyword_checker import run_keyword_checks
            alerts = await run_keyword_checks(new_articles, db)
            if alerts:
                logger.info(f"Scheduler: {alerts} keyword alerts sent")

            # Auto-summarize new articles immediately (up to 30)
            from app.services.summarizer import summarize_pending
            summarized = await summarize_pending(db, limit=min(total, 30))
            logger.info(f"Scheduler: auto-summarized {summarized} articles post-fetch")

            # Broadcast to WebSocket clients
            try:
                from app.api.websocket import manager
                await manager.broadcast("fetch_complete", {
                    "total_new": total, "summarized": summarized
                })
            except Exception as e:
                logger.warning(f"WS broadcast failed: {e}")

            # Push in-app notification
            from app.services.notification_service import push
            push(db, "fetch", "Fetch completado",
                 f"{total} artículos nuevos · {summarized} resumidos automáticamente")

    except Exception as e:
        logger.exception(f"Scheduler fetch error: {e}")
        try:
            from app.services.notification_service import push
            push(db, "error", "Error en fetch", str(e))
        except Exception:
            pass
    finally:
        db.close()


async def job_daily_digest():
    """Send daily digest to owner + all active subscribers."""
    logger.info("Scheduler: sending daily digest")
    db = SessionLocal()
    try:
        cfg = db.query(DigestConfig).first()
        count       = cfg.count     if cfg else 10
        min_score   = cfg.min_score if cfg else 0
        cats_filter = (
            [c.strip() for c in cfg.categories.split(",")]
            if cfg and cfg.categories else None
        )

        query = (
            db.query(Article)
            .options(joinedload(Article.summary))
            .filter(Article.status.in_(["approved", "pending"]))
        )
        if min_score > 0:
            query = query.filter(
                (Article.relevance_score == None) | (Article.relevance_score >= min_score)
            )
        if cats_filter:
            query = query.filter(Article.category.in_(cats_filter))

        articles = query.order_by(Article.fetched_at.desc()).limit(count).all()

        # Send to owner channel
        from app.services.telegram_notifier import send_digest
        await send_digest(articles)

        # Broadcast digest summary to public subscribers
        if articles:
            try:
                from app.services.telegram_bot import broadcast_to_subscribers
                from app.services.telegram_notifier import _esc
                lines = [f"📰 <b>Digest diario — {len(articles)} noticias</b>\n"]
                for i, a in enumerate(articles[:5], 1):
                    summary = ""
                    if a.summary:
                        summary = a.summary.summary_text[:120] + "…"
                    cat = f" · {a.category}" if a.category else ""
                    lines.append(f"<b>{i}. {_esc(a.title)}</b>{cat}")
                    if summary:
                        lines.append(f"   {_esc(summary)}")
                    lines.append(f'   <a href="{a.url}">Leer más</a>\n')
                if len(articles) > 5:
                    lines.append(f"<i>… y {len(articles) - 5} noticias más</i>")
                lines.append("\n💬 /noticias para ver todas · /cancelar para darte de baja")
                await broadcast_to_subscribers("\n".join(lines))
                logger.info("Scheduler: digest broadcast to subscribers")
            except Exception as e:
                logger.warning(f"Subscriber broadcast error: {e}")

        from app.services.notification_service import push
        push(db, "digest", "Digest diario enviado",
             f"{len(articles)} artículos enviados por Telegram")

        logger.info(f"Scheduler: digest sent with {len(articles)} articles")
    except Exception as e:
        logger.exception(f"Scheduler digest error: {e}")
    finally:
        db.close()


def _resolve_db_path() -> Path | None:
    """Resolve the SQLite file path from the configured DATABASE_URL."""
    db_url = settings.database_url
    if db_url.startswith("sqlite:////"):
        return Path(db_url[len("sqlite:////"):])
    elif db_url.startswith("sqlite:///"):
        p = db_url[len("sqlite:///"):]
        return Path(p) if p else None
    return None


async def job_backup_db():
    """
    Daily SQLite backup:
    - If BACKUP_DIR is set → copy to that directory (keep 7 backups)
    - Always → send the .db file to the admin Telegram chat as a document
      so the DB survives even if the hosting filesystem is ephemeral (Render free tier)
    """
    db_path = _resolve_db_path()
    if not db_path or not db_path.exists():
        logger.warning("Backup: DB file not found, skipping")
        return

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # ── Local file backup (if BACKUP_DIR set) ────────────────────────────
    if settings.backup_dir:
        backup_dir = Path(settings.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        dest = backup_dir / f"newslet_{timestamp}.db"
        try:
            shutil.copy2(db_path, dest)
            logger.info(f"Backup: DB copied to {dest}")
        except Exception as e:
            logger.error(f"Backup: local copy failed — {e}")
        # Rotate — keep only 7 most recent
        backups = sorted(backup_dir.glob("newslet_*.db"), key=lambda p: p.stat().st_mtime)
        for old in backups[:-7]:
            try:
                old.unlink()
            except Exception:
                pass

    # ── Telegram backup (always, works on ephemeral filesystems) ─────────
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    try:
        import httpx
        db_bytes = db_path.read_bytes()
        filename = f"newslet_backup_{timestamp}.db"
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendDocument"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                data={
                    "chat_id": settings.telegram_chat_id,
                    "caption": f"🗄️ Backup automático de la DB\n{timestamp} UTC\n{len(db_bytes) // 1024} KB",
                },
                files={"document": (filename, db_bytes, "application/octet-stream")},
            )
        if resp.json().get("ok"):
            logger.info(f"Backup: DB sent to Telegram ({len(db_bytes) // 1024} KB)")
        else:
            logger.warning(f"Backup: Telegram upload failed — {resp.json()}")
    except Exception as e:
        logger.error(f"Backup: Telegram send failed — {e}")



async def job_cleanup():
    """
    Cleanup job: remove rejected articles older than 30 days
    and sent articles older than 60 days to keep DB lean.
    """
    db = SessionLocal()
    try:
        cutoff_rejected = datetime.utcnow() - timedelta(days=30)
        cutoff_sent     = datetime.utcnow() - timedelta(days=60)

        deleted_rejected = (
            db.query(Article)
            .filter(Article.status == "rejected", Article.fetched_at < cutoff_rejected)
            .delete(synchronize_session=False)
        )
        deleted_sent = (
            db.query(Article)
            .filter(Article.status == "sent", Article.fetched_at < cutoff_sent)
            .delete(synchronize_session=False)
        )
        db.commit()

        total_deleted = deleted_rejected + deleted_sent
        if total_deleted > 0:
            logger.info(
                f"Cleanup: removed {deleted_rejected} rejected + {deleted_sent} sent articles"
            )
            from app.services.notification_service import push
            push(db, "info", "Limpieza completada",
                 f"{total_deleted} artículos antiguos eliminados")
    except Exception as e:
        logger.exception(f"Cleanup job error: {e}")
    finally:
        db.close()


async def _job_cluster():
    """Periodic topic clustering."""
    db = SessionLocal()
    try:
        from app.services.topic_clusterer import cluster_articles
        updated = await cluster_articles(db)
        if updated:
            logger.info(f"Scheduler: topic clustering updated {updated} articles")
    except Exception as e:
        logger.error(f"Clustering job error: {e}")
    finally:
        db.close()


def reschedule_digest(hour: int):
    scheduler.reschedule_job("daily_digest", trigger=CronTrigger(hour=hour, minute=0))
    logger.info(f"Daily digest rescheduled to {hour:02d}:00")


def start_scheduler():
    import os

    # Parallel fetch + auto-summarize every N minutes
    scheduler.add_job(
        job_fetch_all,
        IntervalTrigger(minutes=settings.fetch_interval_minutes),
        id="fetch_news", replace_existing=True,
        misfire_grace_time=60,
    )

    # Daily digest — read hour from DB config
    db = SessionLocal()
    try:
        cfg = db.query(DigestConfig).first()
        digest_hour = cfg.hour if cfg else settings.digest_hour
    finally:
        db.close()

    scheduler.add_job(
        job_daily_digest,
        CronTrigger(hour=digest_hour, minute=0),
        id="daily_digest", replace_existing=True,
        misfire_grace_time=300,
    )

    # Topic clustering — every 2 hours
    scheduler.add_job(
        _job_cluster,
        IntervalTrigger(hours=2),
        id="topic_cluster", replace_existing=True,
    )

    # Daily DB backup at 02:00 UTC — auto-enabled on Fly.io if volume exists
    effective_backup_dir = settings.backup_dir or (
        "/app/data/backups" if os.path.isdir("/app/data") else ""
    )
    if effective_backup_dir:
        # Patch settings so job_backup_db picks it up
        object.__setattr__(settings, "backup_dir", effective_backup_dir)
        scheduler.add_job(
            job_backup_db,
            CronTrigger(hour=2, minute=0),
            id="db_backup", replace_existing=True,
        )
        logger.info(f"DB backup scheduled → {effective_backup_dir}")

    # Weekly cleanup — every Sunday at 03:00
    scheduler.add_job(
        job_cleanup,
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="cleanup", replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: fetch every {settings.fetch_interval_minutes}min, "
        f"digest at {digest_hour:02d}:00, cleanup Sundays 03:00"
    )
