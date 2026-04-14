import hashlib
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.orm import Session

from app.models import Article

# Tracking parameters to strip from URLs
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid",
}


def normalize_url(url: str) -> str:
    """Normalize a URL by stripping tracking params, trailing slashes, and lowercasing scheme+host."""
    parsed = urlparse(url)
    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    # Strip tracking params
    params = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {k: v for k, v in params.items() if k.lower() not in TRACKING_PARAMS}
    query = urlencode(filtered, doseq=True)
    # Strip trailing slash from path
    path = parsed.path.rstrip("/")
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def compute_hash(url: str) -> str:
    """Compute SHA-256 hash of a normalized URL."""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def is_duplicate(url: str, db: Session) -> bool:
    """Check if an article with this URL already exists."""
    url_hash = compute_hash(url)
    return db.query(Article.id).filter(Article.url_hash == url_hash).first() is not None
