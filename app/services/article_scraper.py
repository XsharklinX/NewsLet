"""Scrapes the full text of an article URL for better AI summarization."""
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


async def scrape_full_text(url: str) -> str | None:
    """
    Fetch a URL and extract article body text.
    Returns cleaned text (max 8000 chars) or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=_HEADERS)
            resp.raise_for_status()
    except Exception as e:
        logger.debug(f"article_scraper: failed to fetch {url}: {e}")
        return None

    try:
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception:
        return None

    # Remove noise elements
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    # Priority order for article container
    container = (
        soup.find("article")
        or soup.find(attrs={"class": lambda c: c and "article" in str(c).lower()})
        or soup.find("main")
        or soup.body
    )
    if not container:
        return None

    text = container.get_text(separator="\n", strip=True)
    # Collapse blank lines
    lines = [line for line in text.splitlines() if line.strip()]
    cleaned = "\n".join(lines)

    # Minimum useful length
    if len(cleaned) < 100:
        return None

    return cleaned[:8000]
