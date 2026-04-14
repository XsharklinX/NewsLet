import asyncio
import logging
from datetime import datetime
from time import mktime

import feedparser
from sqlalchemy.orm import Session

from app.models import Article, Source
from app.services.deduplicator import compute_hash, is_duplicate

logger = logging.getLogger(__name__)


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


async def fetch_rss_source(source: Source, db: Session) -> int:
    """Fetch a single RSS source. Returns number of new articles inserted."""
    logger.info(f"Fetching RSS: {source.name} ({source.url})")
    entries = await asyncio.to_thread(_parse_feed, source.url)

    new_count = 0
    for entry in entries:
        if not entry["url"]:
            continue
        if is_duplicate(entry["url"], db):
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
    logger.info(f"  -> {new_count} new articles from {source.name}")
    return new_count


async def fetch_all_rss(db: Session) -> int:
    """Fetch all active RSS sources. Returns total new articles."""
    sources = db.query(Source).filter(Source.source_type == "rss", Source.is_active == True).all()
    total = 0
    for source in sources:
        try:
            count = await fetch_rss_source(source, db)
            total += count
        except Exception as e:
            logger.error(f"Error fetching {source.name}: {e}")
    return total
