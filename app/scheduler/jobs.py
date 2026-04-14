import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import SessionLocal
from app.models import Article, DigestConfig

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def job_fetch_all():
    """
    Full fetch pipeline:
    1. Parallel fetch from all sources
    2. Keyword alerts on new articles
    3. Auto-summarize new articles immediately
    4. Broadcast live update via WebSocket
    5. Push in-app notification
    """
    logger.info("Scheduler: starting fetch cycle")
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=settings.fetch_interval_minutes + 2)

        from app.services.rss_fetcher import fetch_all_rss
        from app.services.newsapi_fetcher import fetch_all_newsapi
        from app.services.web_scraper import fetch_all_scrapers

        # Run all fetchers in parallel
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
    """Send daily digest respecting DigestConfig settings."""
    logger.info("Scheduler: sending daily digest")
    db = SessionLocal()
    try:
        cfg = db.query(DigestConfig).first()
        count      = cfg.count     if cfg else 10
        min_score  = cfg.min_score if cfg else 0
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

        from app.services.telegram_notifier import send_digest
        await send_digest(articles)

        from app.services.notification_service import push
        push(db, "digest", "Digest diario enviado",
             f"{len(articles)} artículos enviados por Telegram")

        logger.info(f"Scheduler: digest sent with {len(articles)} articles")
    except Exception as e:
        logger.exception(f"Scheduler digest error: {e}")
    finally:
        db.close()


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


def reschedule_digest(hour: int):
    scheduler.reschedule_job("daily_digest", trigger=CronTrigger(hour=hour, minute=0))
    logger.info(f"Daily digest rescheduled to {hour:02d}:00")


def start_scheduler():
    # Parallel fetch + auto-summarize every N minutes
    scheduler.add_job(
        job_fetch_all,
        IntervalTrigger(minutes=settings.fetch_interval_minutes),
        id="fetch_news", replace_existing=True,
        misfire_grace_time=60,
    )

    # Daily digest
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
