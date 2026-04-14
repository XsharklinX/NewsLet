"""Scrapes the full text and Open Graph thumbnail of an article URL."""
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_NOISE_TAGS = [
    "script", "style", "nav", "header", "footer", "aside",
    "form", "iframe", "noscript", "figure", "figcaption",
    "button", "input", "select", "textarea", "advertisement",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


def _extract_thumbnail(soup: BeautifulSoup) -> str | None:
    """Extract Open Graph or Twitter Card thumbnail URL from parsed HTML."""
    # og:image (standard)
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"].strip()

    # twitter:image (fallback)
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return tw["content"].strip()

    # twitter:image:src (another variant)
    tw2 = soup.find("meta", attrs={"name": "twitter:image:src"})
    if tw2 and tw2.get("content"):
        return tw2["content"].strip()

    return None


async def scrape_article(url: str) -> tuple[str | None, str | None]:
    """
    Fetch a URL and extract:
    - full article text (max 8000 chars)
    - thumbnail URL from Open Graph / Twitter Card meta tags

    Returns (text, thumbnail_url). Either can be None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=_HEADERS)
            resp.raise_for_status()
    except Exception as e:
        logger.debug(f"article_scraper: failed to fetch {url}: {e}")
        return None, None

    try:
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        return None, None

    # Extract thumbnail BEFORE removing noise tags
    thumbnail = _extract_thumbnail(soup)

    # Remove noise elements for text extraction
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    # Priority order for article container
    container = (
        soup.find("article")
        or soup.find(attrs={"class": lambda c: c and "article" in str(c).lower()})
        or soup.find("main")
        or soup.body
    )

    text = None
    if container:
        raw_text = container.get_text(separator="\n", strip=True)
        lines = [line for line in raw_text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        if len(cleaned) >= 100:
            text = cleaned[:8000]

    return text, thumbnail


async def scrape_full_text(url: str) -> str | None:
    """Backward-compatible wrapper — returns only full text."""
    text, _ = await scrape_article(url)
    return text
