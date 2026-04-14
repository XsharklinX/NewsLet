import hashlib
import logging
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.orm import Session

from app.models import Article

logger = logging.getLogger(__name__)

# Tracking parameters to strip from URLs
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid",
}

# Fuzzy title similarity threshold (0-100). Titles with score >= this are considered duplicates.
FUZZY_THRESHOLD = 85

# Look back window for fuzzy title comparison (days)
FUZZY_LOOKBACK_DAYS = 7


def normalize_url(url: str) -> str:
    """Normalize a URL by stripping tracking params, trailing slashes, and lowercasing scheme+host."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    params = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {k: v for k, v in params.items() if k.lower() not in TRACKING_PARAMS}
    query = urlencode(filtered, doseq=True)
    path = parsed.path.rstrip("/")
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def compute_hash(url: str) -> str:
    """Compute SHA-256 hash of a normalized URL."""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def is_duplicate(url: str, db: Session, title: str | None = None) -> bool:
    """
    Check if an article already exists via:
    1. Exact SHA-256 URL hash match (fast)
    2. Fuzzy title similarity against recent articles (rapidfuzz, optional)
    """
    # Fast path: exact URL hash
    url_hash = compute_hash(url)
    if db.query(Article.id).filter(Article.url_hash == url_hash).first() is not None:
        return True

    # Fuzzy title check (only when title is provided and rapidfuzz is available)
    if title:
        try:
            from rapidfuzz import fuzz

            cutoff = datetime.utcnow() - timedelta(days=FUZZY_LOOKBACK_DAYS)
            recent_titles = (
                db.query(Article.title)
                .filter(Article.fetched_at >= cutoff)
                .all()
            )
            for (existing_title,) in recent_titles:
                if not existing_title:
                    continue
                score = fuzz.token_sort_ratio(title.lower(), existing_title.lower())
                if score >= FUZZY_THRESHOLD:
                    logger.debug(
                        f"Fuzzy duplicate detected (score={score}): "
                        f"'{title[:60]}' ≈ '{existing_title[:60]}'"
                    )
                    return True
        except ImportError:
            pass  # rapidfuzz not installed, skip fuzzy check

    return False
