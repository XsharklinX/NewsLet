"""
Keyword-based topic clustering.
Groups recent articles by shared significant keywords.
Each cluster gets an integer ID (hash of its keyword fingerprint).
"""
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Article

logger = logging.getLogger(__name__)

# Spanish + English stopwords
_STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "del", "las", "un", "por",
    "con", "una", "su", "para", "es", "al", "lo", "como", "más", "mas",
    "pero", "sus", "le", "ya", "o", "fue", "este", "ha", "se", "que",
    "entre", "cuando", "muy", "sin", "sobre", "ser", "tiene", "también",
    "hasta", "hay", "donde", "han", "quien", "están", "estado", "desde",
    "todo", "nos", "durante", "estados", "todos", "uno", "les", "ni",
    "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mi",
    "antes", "algunos", "unos", "yo", "otro", "otras", "the", "of", "and",
    "to", "in", "a", "is", "that", "for", "on", "at", "by", "it", "or",
    "an", "be", "as", "was", "with", "are", "this", "has", "have", "had",
    "not", "but", "its", "from", "were", "they", "been", "their", "which",
    "new", "nuevo", "nueva", "tras", "según", "segun", "ante", "puede",
    "pudo", "dijo", "afirmó", "señaló", "indicó", "aseguró",
}

# Minimum word length for significant keywords
_MIN_WORD_LEN = 4

# Minimum shared keywords to group articles
_MIN_OVERLAP = 2

# Days lookback for clustering
_LOOKBACK_DAYS = 3

# Top-N keywords per article to use
_TOP_KEYWORDS = 10


def _extract_keywords(title: str, text: str | None = None) -> set[str]:
    """Extract significant keywords from title + text."""
    combined = f"{title} {text or ''}".lower()
    words = re.findall(r"[a-záéíóúñü]{4,}", combined)
    return {w for w in words if w not in _STOPWORDS and len(w) >= _MIN_WORD_LEN}


async def cluster_articles(db: Session, lookback_days: int = _LOOKBACK_DAYS) -> int:
    """
    Group recent articles by shared keywords and assign cluster_ids.
    Returns the number of articles that received a cluster_id.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    articles = (
        db.query(Article)
        .filter(Article.fetched_at >= cutoff)
        .order_by(Article.fetched_at.desc())
        .all()
    )

    if not articles:
        return 0

    # Extract keywords for each article
    article_keywords: dict[int, set[str]] = {}
    for art in articles:
        kws = _extract_keywords(art.title, art.original_text or art.full_text)
        if kws:
            article_keywords[art.id] = set(list(kws)[:_TOP_KEYWORDS])

    # Union-Find for grouping
    parent: dict[int, int] = {a.id: a.id for a in articles}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Pairwise overlap check
    ids = [a.id for a in articles if a.id in article_keywords]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a_id, b_id = ids[i], ids[j]
            overlap = article_keywords[a_id] & article_keywords[b_id]
            if len(overlap) >= _MIN_OVERLAP:
                union(a_id, b_id)

    # Assign cluster IDs (only to groups with 2+ members)
    groups: dict[int, list[int]] = defaultdict(list)
    for art_id in ids:
        root = find(art_id)
        groups[root].append(art_id)

    cluster_map: dict[int, int] = {}  # article_id → cluster_id
    for root, members in groups.items():
        if len(members) >= 2:
            cluster_id = root  # use root article ID as cluster ID
            for art_id in members:
                cluster_map[art_id] = cluster_id

    # Persist cluster assignments
    id_to_art = {a.id: a for a in articles}
    updated = 0
    for art_id, cluster_id in cluster_map.items():
        art = id_to_art.get(art_id)
        if art and art.cluster_id != cluster_id:
            art.cluster_id = cluster_id
            updated += 1

    # Clear cluster_id for articles that are no longer in a cluster
    for art in articles:
        if art.id not in cluster_map and art.cluster_id is not None:
            art.cluster_id = None

    if updated > 0:
        db.commit()

    logger.info(
        f"Topic clustering: {updated} articles updated, "
        f"{len(groups)} groups found in last {lookback_days}d"
    )
    return updated
