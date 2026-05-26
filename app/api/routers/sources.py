import asyncio
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import feedparser
import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article, Source
from app.schemas.article import SourceCreate, SourceOut, SourceStatsOut
from app.services.auth import require_auth

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_auth)],
)


# ═══════════════════════════════════════════════════════════════════════════
# SOURCES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/sources", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return db.query(Source).order_by(Source.name).all()


@router.post("/sources", response_model=SourceOut, status_code=201)
def create_source(body: SourceCreate, db: Session = Depends(get_db)):
    source = Source(name=body.name, source_type=body.source_type, url=body.url)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.patch("/sources/{source_id}/toggle", response_model=SourceOut)
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).get(source_id)
    if not source:
        raise HTTPException(404, "Fuente no encontrada")
    source.is_active = not source.is_active
    db.commit()
    db.refresh(source)
    return source


@router.get("/sources/{source_id}/stats", response_model=SourceStatsOut)
def source_stats(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).get(source_id)
    if not source:
        raise HTTPException(404, "Fuente no encontrada")

    articles = db.query(Article).filter(Article.source_id == source_id).all()
    total = len(articles)

    scored = [a.relevance_score for a in articles if a.relevance_score is not None]
    avg_score = round(sum(scored) / len(scored), 1) if scored else None

    week_ago = datetime.utcnow() - timedelta(days=7)
    articles_week = sum(1 for a in articles if a.fetched_at and a.fetched_at >= week_ago)

    rejected = sum(1 for a in articles if a.status == "rejected")
    rejection_rate = round(rejected / total * 100) if total > 0 else 0

    cats: dict[str, int] = {}
    sents: dict[str, int] = {}
    for a in articles:
        if a.category:
            cats[a.category] = cats.get(a.category, 0) + 1
        if a.sentiment:
            sents[a.sentiment] = sents.get(a.sentiment, 0) + 1

    return SourceStatsOut(
        source_id=source_id, name=source.name,
        total_articles=total, avg_score=avg_score,
        articles_week=articles_week, rejection_rate=rejection_rate,
        categories=cats, sentiments=sents,
    )


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).get(source_id)
    if not source:
        raise HTTPException(404, "Fuente no encontrada")
    db.delete(source)
    db.commit()
    return {"message": "Fuente eliminada", "source_id": source_id}


# ═══════════════════════════════════════════════════════════════════════════
# OPML IMPORT
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/sources/opml", status_code=201)
async def import_opml(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import RSS sources from an OPML file."""
    content = await file.read()
    try:
        root = ET.fromstring(content.decode("utf-8", errors="replace"))
    except ET.ParseError as e:
        raise HTTPException(400, f"OPML inválido: {e}")

    existing_urls = {s.url for s in db.query(Source.url).all()}
    added = []
    for outline in root.iter("outline"):
        url = outline.get("xmlUrl") or outline.get("url")
        name = outline.get("title") or outline.get("text") or "Sin nombre"
        if url and url not in existing_urls:
            src = Source(name=name[:200], source_type="rss", url=url)
            db.add(src)
            existing_urls.add(url)
            added.append(name)

    db.commit()
    return {"added": len(added), "sources": added[:20]}


# ═══════════════════════════════════════════════════════════════════════════
# SOURCE HEALTH
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/sources/health")
def sources_health(db: Session = Depends(get_db)):
    """Return health status of all sources."""
    sources = db.query(Source).order_by(Source.consecutive_failures.desc()).all()
    return {
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "is_active": s.is_active,
                "consecutive_failures": s.consecutive_failures or 0,
                "last_error": s.last_error,
                "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
                "disabled_at": s.disabled_at.isoformat() if s.disabled_at else None,
            }
            for s in sources
        ]
    }


@router.post("/sources/{source_id}/reenable")
def reenable_source(source_id: int, db: Session = Depends(get_db)):
    """Re-enable a source that was auto-disabled."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(404, "Fuente no encontrada")
    source.is_active = True
    source.consecutive_failures = 0
    source.last_error = None
    source.disabled_at = None
    db.commit()
    return {"id": source_id, "is_active": True}


# ═══════════════════════════════════════════════════════════════════════════
# SOURCE PREVIEW — test fetch before saving
# ═══════════════════════════════════════════════════════════════════════════

_YT_PATTERNS = [
    re.compile(r"youtube\.com/channel/([A-Za-z0-9_-]+)"),
    re.compile(r"youtube\.com/@([A-Za-z0-9_.-]+)"),
    re.compile(r"youtube\.com/c/([A-Za-z0-9_.-]+)"),
    re.compile(r"youtube\.com/user/([A-Za-z0-9_.-]+)"),
]


def _youtube_to_rss(url: str) -> str | None:
    """Convert a YouTube channel/user URL to its RSS feed URL."""
    m = _YT_PATTERNS[0].search(url)
    if m:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={m.group(1)}"
    for pat in _YT_PATTERNS[1:]:
        if pat.search(url):
            return None  # need channel_id — handled client-side with a hint
    return None


class PreviewRequest(BaseModel):
    url: str
    source_type: str = "rss"


@router.post("/sources/preview")
async def preview_source(body: PreviewRequest):
    """Fetch a source URL and return a sample of its articles (no DB write)."""
    url = body.url.strip()

    # YouTube URL detection
    yt_rss = _youtube_to_rss(url)
    resolved_url = yt_rss or url
    is_youtube = bool(yt_rss)

    if body.source_type == "rss":
        try:
            def _parse():
                return feedparser.parse(resolved_url)

            feed = await asyncio.wait_for(asyncio.to_thread(_parse), timeout=15)
            if feed.bozo and not feed.entries:
                raise HTTPException(400, f"No se pudo parsear el feed: {feed.bozo_exception}")
            if not feed.entries:
                raise HTTPException(400, "El feed está vacío o no es RSS válido")

            articles = []
            for e in feed.entries[:5]:
                published = None
                if hasattr(e, "published_parsed") and e.published_parsed:
                    from time import mktime
                    published = datetime.fromtimestamp(mktime(e.published_parsed)).isoformat()
                articles.append({
                    "title":        e.get("title", "Sin título"),
                    "url":          e.get("link", ""),
                    "summary":      (e.get("summary") or "")[:300],
                    "published_at": published,
                })

            feed_title = feed.feed.get("title", "") or ""
            return {
                "ok": True,
                "feed_title": feed_title,
                "total_entries": len(feed.entries),
                "resolved_url": resolved_url,
                "is_youtube": is_youtube,
                "articles": articles,
            }
        except HTTPException:
            raise
        except asyncio.TimeoutError:
            raise HTTPException(408, "Timeout al cargar el feed (>15s)")
        except Exception as e:
            raise HTTPException(400, f"Error al cargar el feed: {e}")

    elif body.source_type == "newsapi":
        from app.config import settings
        if not settings.newsapi_key:
            raise HTTPException(400, "NEWSAPI_KEY no configurada")
        try:
            params = json.loads(url)
        except Exception:
            raise HTTPException(400, "Para NewsAPI la URL debe ser JSON con los parámetros de consulta")
        params["apiKey"] = settings.newsapi_key
        params["pageSize"] = 3
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get("https://newsapi.org/v2/everything", params=params)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            raise HTTPException(400, f"Error NewsAPI: {e}")
        arts = data.get("articles", [])
        return {
            "ok": True,
            "feed_title": f"NewsAPI — {params.get('q', '')}",
            "total_entries": data.get("totalResults", 0),
            "resolved_url": url,
            "is_youtube": False,
            "articles": [{"title": a.get("title",""), "url": a.get("url",""),
                          "summary": (a.get("description") or "")[:300],
                          "published_at": a.get("publishedAt")} for a in arts[:5]],
        }
    else:
        raise HTTPException(400, f"Tipo '{body.source_type}' no soportado en preview")


# ═══════════════════════════════════════════════════════════════════════════
# CURATED SOURCES CATALOGUE
# ═══════════════════════════════════════════════════════════════════════════

POPULAR_SOURCES = [
    # España
    {"name": "El País", "source_type": "rss", "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",   "category": "España"},
    {"name": "El Mundo", "source_type": "rss", "url": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",               "category": "España"},
    {"name": "El Confidencial", "source_type": "rss", "url": "https://www.elconfidencial.com/rss/espana.xml",               "category": "España"},
    {"name": "elDiario.es", "source_type": "rss", "url": "https://www.eldiario.es/rss/",                                   "category": "España"},
    {"name": "La Vanguardia", "source_type": "rss", "url": "https://www.lavanguardia.com/rss/home.xml",                    "category": "España"},
    # Internacional
    {"name": "BBC Mundo", "source_type": "rss", "url": "https://feeds.bbci.co.uk/mundo/rss.xml",                           "category": "Internacional"},
    {"name": "Reuters ES", "source_type": "rss", "url": "https://es.reuters.com/rssFeed/worldNews",                        "category": "Internacional"},
    {"name": "DW Español", "source_type": "rss", "url": "https://rss.dw.com/rdf/rss-es-all",                               "category": "Internacional"},
    {"name": "CNN Español", "source_type": "rss", "url": "http://cnnespanol.cnn.com/feed/",                                "category": "Internacional"},
    # Tecnología
    {"name": "Xataka", "source_type": "rss", "url": "https://www.xataka.com/index.xml",                                    "category": "Tecnología"},
    {"name": "Genbeta", "source_type": "rss", "url": "https://www.genbeta.com/index.xml",                                  "category": "Tecnología"},
    {"name": "Hipertextual", "source_type": "rss", "url": "https://hipertextual.com/feed",                                 "category": "Tecnología"},
    {"name": "MIT Tech Review ES", "source_type": "rss", "url": "https://www.technologyreview.es/feed/",                   "category": "Tecnología"},
    # Economía
    {"name": "Expansión", "source_type": "rss", "url": "https://e00-expansion.uecdn.es/rss/portada.xml",                  "category": "Economía"},
    {"name": "Cinco Días", "source_type": "rss", "url": "https://cincodias.elpais.com/rss/cincodias/ultima_hora.xml",     "category": "Economía"},
    # Ciencia
    {"name": "National Geographic ES", "source_type": "rss", "url": "https://www.nationalgeographic.com.es/rss/20",       "category": "Ciencia"},
    {"name": "Materia (El País)", "source_type": "rss", "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada", "category": "Ciencia"},
]


@router.get("/sources/catalogue")
def sources_catalogue():
    """Return a curated list of popular RSS sources to quick-add."""
    return {"sources": POPULAR_SOURCES}
