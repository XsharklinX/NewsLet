import asyncio
import logging
from datetime import datetime
from time import mktime

import feedparser
from sqlalchemy.orm import Session

from app.models import Article, Source
from app.services.deduplicator import compute_hash, is_duplicate

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 5


def _parse_feed(url: str) -> list[dict]:
    """Parse an RSS feed and return entries as dicts. Runs synchronously."""
    feed = feedparser.parse(url)
    entries = []
    for entry in feed.entries:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime.fromtimestamp(mktime(entry.published_parsed))

        entries.append({
            "title": entry.get("title", "Sin titulo"),
            "url": entry.get("link", ""),
            "text": entry.get("summary", entry.get("description", "")),
            "published_at": published,
        })
    return entries


def _record_success(source: Source, db: Session) -> None:
    source.consecutive_failures = 0
    source.last_error = None
    source.last_success_at = datetime.utcnow()
    db.commit()


def _record_failure(source: Source, db: Session, error: str) -> None:
    source.consecutive_failures = (source.consecutive_failures or 0) + 1
    source.last_error = error[:500]
    if source.consecutive_failures >= MAX_CONSECUTIVE_FAILURES and source.is_active:
        source.is_active = False
        source.disabled_at = datetime.utcnow()
        logger.warning(
            f"Source '{source.name}' auto-disabled after "
            f"{source.consecutive_failures} consecutive failures"
        )
    db.commit()


_SOURCE_TIMEOUT = 30  # seconds per source


async def fetch_rss_source(source: Source, db: Session) -> int:
    """Fetch a single RSS source with a per-source timeout. Returns new article count."""
    logger.info(f"Fetching RSS: {source.name} ({source.url})")
    try:
        entries = await asyncio.wait_for(
            asyncio.to_thread(_parse_feed, source.url),
            timeout=_SOURCE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        err = f"Timeout after {_SOURCE_TIMEOUT}s"
        _record_failure(source, db, err)
        logger.warning(f"RSS timeout: {source.name}")
        return 0
    except Exception as e:
        _record_failure(source, db, str(e))
        logger.error(f"Error fetching {source.name}: {e}")
        return 0

    new_count = 0
    for entry in entries:
        if not entry["url"]:
            continue
        if is_duplicate(entry["url"], db, title=entry["title"]):
            continue

        article = Article(
            source_id=source.id,
            title=entry["title"],
            url=entry["url"],
            url_hash=compute_hash(entry["url"]),
            original_text=entry["text"],
            published_at=entry["published_at"],
            fetched_at=datetime.utcnow(),
            status="pending",
        )
        db.add(article)
        new_count += 1

    if new_count > 0:
        db.commit()

    _record_success(source, db)
    logger.info(f"  -> {new_count} new articles from {source.name}")
    return new_count


_MAX_CONCURRENT = 5  # max parallel RSS fetches to avoid hammering


async def fetch_all_rss(db: Session) -> int:
    """Fetch all active RSS sources with bounded concurrency. Returns total new articles."""
    sources = db.query(Source).filter(
        Source.source_type == "rss", Source.is_active == True
    ).all()

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def _bounded(source: Source) -> int:
        async with semaphore:
            try:
                return await fetch_rss_source(source, db)
            except Exception as e:
                logger.error(f"fetch_all_rss unexpected error for {source.name}: {e}")
                return 0

    results = await asyncio.gather(*(_bounded(s) for s in sources), return_exceptions=True)
    return sum(r for r in results if isinstance(r, int))
