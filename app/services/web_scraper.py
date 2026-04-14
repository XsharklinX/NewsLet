import json
import logging
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models import Article, Source
from app.services.deduplicator import compute_hash, is_duplicate

logger = logging.getLogger(__name__)

# Default scraper configs for known sites
SCRAPER_PRESETS = {
    "wordpress": {
        "article_selector": "article",
        "title_selector": ".entry-title a",
        "link_selector": ".entry-title a",
        "link_attr": "href",
        "excerpt_selector": ".entry-content p, .entry-excerpt, .td-excerpt",
        "date_selector": "time, .entry-date, .td-post-date",
        "image_selector": "img.wp-post-image, .entry-thumb, .td-module-thumb img",
        "image_attr": "src",
    },
    "generic": {
        "article_selector": "article, .post, .article, .news-item",
        "title_selector": "h2 a, h3 a, .title a",
        "link_selector": "h2 a, h3 a, .title a",
        "link_attr": "href",
        "excerpt_selector": "p, .excerpt, .summary, .description",
        "date_selector": "time, .date, .post-date",
        "image_selector": "img",
        "image_attr": "src",
    },
}


def _get_scraper_config(source: Source) -> dict:
    """Parse scraper config from source.url JSON field."""
    try:
        config = json.loads(source.url)
    except json.JSONDecodeError:
        return {}
    return config


async def fetch_scraper_source(source: Source, db: Session) -> int:
    """Scrape a website for articles. Returns number of new articles inserted."""
    config = _get_scraper_config(source)
    target_url = config.get("target_url", "")
    preset = config.get("preset", "generic")

    if not target_url:
        logger.error(f"Scraper source {source.name} has no target_url")
        return 0

    selectors = {**SCRAPER_PRESETS.get(preset, SCRAPER_PRESETS["generic"])}
    # Allow per-source selector overrides
    for key in SCRAPER_PRESETS["generic"]:
        if key in config:
            selectors[key] = config[key]

    logger.info(f"Scraping: {source.name} ({target_url})")

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(target_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; NewsBotPro/1.0)"
        })
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    articles_el = soup.select(selectors["article_selector"])

    new_count = 0
    for el in articles_el[:30]:  # Limit to 30 articles per scrape
        # Title
        title_el = el.select_one(selectors["title_selector"])
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        # Link
        link_el = el.select_one(selectors["link_selector"])
        if not link_el:
            continue
        url = link_el.get(selectors["link_attr"], "")
        if not url:
            continue
        # Handle relative URLs
        if url.startswith("/"):
            from urllib.parse import urljoin
            url = urljoin(target_url, url)

        if is_duplicate(url, db):
            continue

        # Excerpt
        excerpt_el = el.select_one(selectors["excerpt_selector"])
        excerpt = excerpt_el.get_text(strip=True) if excerpt_el else ""

        # Date
        date_el = el.select_one(selectors["date_selector"])
        published = None
        if date_el:
            date_str = date_el.get("datetime") or date_el.get_text(strip=True)
            try:
                published = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Image
        img_el = el.select_one(selectors["image_selector"])
        image_url = ""
        if img_el:
            image_url = img_el.get(selectors["image_attr"]) or img_el.get("data-src", "")

        # Build text with image metadata
        text = excerpt
        if image_url:
            text = f"[IMG:{image_url}]\n{text}"

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
    logger.info(f"  -> {new_count} new articles scraped from {source.name}")
    return new_count


async def fetch_all_scrapers(db: Session) -> int:
    """Fetch all active scraper sources. Returns total new articles."""
    sources = db.query(Source).filter(Source.source_type == "scraper", Source.is_active == True).all()
    total = 0
    for source in sources:
        try:
            count = await fetch_scraper_source(source, db)
            total += count
        except Exception as e:
            logger.error(f"Error scraping {source.name}: {e}")
    return total
