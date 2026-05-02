import hashlib
import json
import logging
import time
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Article, Source
from app.services.deduplicator import compute_hash, is_duplicate

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2/everything"
MAX_CONSECUTIVE_FAILURES = 5
_NEWSAPI_CACHE: dict[str, tuple[float, list]] = {}
_CACHE_TTL = 900  # 15 minutes


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


async def fetch_newsapi_source(source: Source, db: Session) -> int:
    """Fetch a single NewsAPI source. Returns number of new articles inserted."""
    logger.info(f"Fetching NewsAPI: {source.name}")

    # Source.url stores JSON query params
    try:
        params = json.loads(source.url)
    except json.JSONDecodeError:
        error_msg = f"Invalid JSON in source URL for {source.name}: {source.url}"
        logger.error(error_msg)
        _record_failure(source, db, error_msg)
        return 0

    params["apiKey"] = settings.newsapi_key
    if not params.get("pageSize"):
        params["pageSize"] = 20

    cache_key = hashlib.md5(json.dumps(sorted(params.items())).encode()).hexdigest()
    now = time.monotonic()
    if cache_key in _NEWSAPI_CACHE:
        ts, cached_articles = _NEWSAPI_CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            logger.debug(f"NewsAPI cache hit: {source.name}")
            articles_data = cached_articles
        else:
            articles_data = None
    else:
        articles_data = None

    if articles_data is None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(NEWSAPI_BASE, params=params)
                resp.raise_for_status()
                data = resp.json()
            articles_data = data.get("articles", [])
            _NEWSAPI_CACHE[cache_key] = (time.monotonic(), articles_data)
        except Exception as e:
            _record_failure(source, db, str(e))
            logger.error(f"Error fetching NewsAPI {source.name}: {e}")
            return 0

    new_count = 0
    for item in articles_data:
        url = item.get("url", "")
        title = item.get("title", "Sin titulo")
        if not url:
            continue
        if is_duplicate(url, db, title=title):
            continue

        published = None
        if item.get("publishedAt"):
            try:
                published = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
            except ValueError:
                pass

        # Combine description + content for better summaries
        text_parts = [item.get("description", ""), item.get("content", "")]
        text = "\n".join(p for p in text_parts if p)

        article = Article(
            source_id=source.id,
            title=title,
            url=url,
            url_hash=compute_hash(url),
            original_text=text,
            published_at=published,
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


async def fetch_all_newsapi(db: Session) -> int:
    """Fetch all active NewsAPI sources. Returns total new articles."""
    sources = db.query(Source).filter(Source.source_type == "newsapi", Source.is_active == True).all()
    total = 0
    for source in sources:
        try:
            count = await fetch_newsapi_source(source, db)
            total += count
        except Exception as e:
            logger.error(f"Error fetching NewsAPI {source.name}: {e}")
    return total
