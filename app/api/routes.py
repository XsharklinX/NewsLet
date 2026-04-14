import csv
import io
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import cast, Date, func, extract
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import Article, DigestConfig, Keyword, Source, Summary
from app.models.article import VALID_CATEGORIES
from app.models.notification import Notification
from app.models.webhook import Webhook
from app.schemas.article import (
    ArticleListOut, ArticleOut, ArticleStatusUpdate,
    ChartOut, DigestConfigOut, DigestConfigUpdate,
    HeatmapOut, HeatmapHourPoint, HeatmapDayPoint,
    KeywordCreate, KeywordOut,
    NotificationOut,
    SourceCreate, SourceOut, SourceStatsOut, StatsOut,
    TrendingOut, TrendingTopic,
    WebhookCreate, WebhookOut,
)

router = APIRouter(prefix="/api/v1")

# Spanish stopwords for trending
_STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "los", "del", "las", "un", "por",
    "con", "una", "su", "para", "es", "al", "lo", "como", "más", "mas",
    "pero", "sus", "le", "ya", "o", "fue", "este", "ha", "se", "que",
    "entre", "cuando", "muy", "sin", "sobre", "ser", "tiene", "también",
    "también", "hasta", "hay", "donde", "han", "quien", "están", "estado",
    "desde", "todo", "nos", "durante", "estados", "todos", "uno", "les",
    "ni", "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto",
    "mi", "antes", "algunos", "qué", "unos", "yo", "otro", "otras",
    "the", "of", "and", "to", "in", "a", "is", "that", "for", "on",
}


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/articles", response_model=ArticleListOut)
def list_articles(
    status: str | None = None,
    source_id: int | None = None,
    category: str | None = None,
    sentiment: str | None = None,
    min_score: int | None = Query(None, ge=1, le=10),
    search: str | None = Query(None, max_length=200),
    date_from: str | None = Query(None, description="ISO datetime — only articles fetched after this"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Article).options(joinedload(Article.summary), joinedload(Article.source))
    if status:
        query = query.filter(Article.status == status)
    if source_id:
        query = query.filter(Article.source_id == source_id)
    if category:
        query = query.filter(Article.category == category)
    if sentiment:
        query = query.filter(Article.sentiment == sentiment)
    if min_score is not None:
        query = query.filter(Article.relevance_score >= min_score)
    if search:
        query = query.filter(
            Article.title.ilike(f"%{search}%") |
            Article.original_text.ilike(f"%{search}%") |
            Article.full_text.ilike(f"%{search}%")
        )
    if date_from:
        try:
            from datetime import datetime as _dt
            cutoff = _dt.fromisoformat(date_from.replace("Z", "+00:00")).replace(tzinfo=None)
            query = query.filter(Article.fetched_at >= cutoff)
        except ValueError:
            pass

    total = query.count()
    articles = (
        query.order_by(Article.fetched_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ArticleListOut(articles=articles, total=total, page=page, page_size=page_size)


@router.get("/articles/export/csv")
def export_articles_csv(
    status: str | None = None,
    category: str | None = None,
    min_score: int | None = Query(None, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Export filtered articles as CSV."""
    query = db.query(Article).options(joinedload(Article.summary), joinedload(Article.source))
    if status:
        query = query.filter(Article.status == status)
    if category:
        query = query.filter(Article.category == category)
    if min_score is not None:
        query = query.filter(Article.relevance_score >= min_score)

    articles = query.order_by(Article.fetched_at.desc()).limit(5000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "title", "url", "source", "category", "score", "sentiment",
        "status", "published_at", "fetched_at", "summary",
    ])
    for a in articles:
        writer.writerow([
            a.id, a.title, a.url,
            a.source.name if a.source else "",
            a.category or "", a.relevance_score or "", a.sentiment or "",
            a.status,
            a.published_at.isoformat() if a.published_at else "",
            a.fetched_at.isoformat(),
            (a.summary.summary_text if a.summary else "").replace("\n", " "),
        ])

    filename = f"newslet_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        content=output.getvalue().encode("utf-8-sig"),   # BOM for Excel compatibility
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/articles/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = (
        db.query(Article)
        .options(joinedload(Article.summary), joinedload(Article.source))
        .get(article_id)
    )
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    return article


@router.get("/articles/{article_id}/related", response_model=list[ArticleOut])
def related_articles(article_id: int, db: Session = Depends(get_db)):
    """Return up to 5 articles in the same category (excluding self)."""
    article = db.query(Article).get(article_id)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")

    cutoff = datetime.utcnow() - timedelta(days=14)
    query = (
        db.query(Article)
        .options(joinedload(Article.summary), joinedload(Article.source))
        .filter(
            Article.id != article_id,
            Article.fetched_at >= cutoff,
        )
    )
    if article.category:
        query = query.filter(Article.category == article.category)

    return query.order_by(Article.relevance_score.desc().nulls_last()).limit(5).all()


@router.patch("/articles/{article_id}/status", response_model=ArticleOut)
def update_article_status(article_id: int, body: ArticleStatusUpdate, db: Session = Depends(get_db)):
    article = db.query(Article).get(article_id)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    article.status = body.status
    db.commit()
    db.refresh(article)
    return article


@router.post("/articles/bulk-approve")
def bulk_approve(ids: list[int], db: Session = Depends(get_db)):
    """Approve multiple articles at once."""
    updated = (
        db.query(Article)
        .filter(Article.id.in_(ids), Article.status == "pending")
        .update({"status": "approved"}, synchronize_session=False)
    )
    db.commit()
    return {"approved": updated, "ids": ids}


@router.post("/articles/bulk-reject")
def bulk_reject(ids: list[int], db: Session = Depends(get_db)):
    """Reject multiple articles at once."""
    updated = (
        db.query(Article)
        .filter(Article.id.in_(ids))
        .update({"status": "rejected"}, synchronize_session=False)
    )
    db.commit()
    return {"rejected": updated, "ids": ids}


@router.post("/articles/bulk-reenrich")
async def bulk_reenrich(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Re-enrich articles missing sentiment or category. Returns count updated."""
    from app.services.summarizer import reenrich_articles
    count = await reenrich_articles(db, limit=limit)
    return {"reenriched": count}


@router.post("/articles/{article_id}/summarize", response_model=ArticleOut)
async def summarize_one(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).options(joinedload(Article.summary)).get(article_id)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    if article.summary:
        db.delete(article.summary)
        db.commit()
        db.refresh(article)
    from app.services.summarizer import summarize_article
    await summarize_article(article, db)
    db.refresh(article)
    return article


@router.post("/articles/{article_id}/send")
async def send_one(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).options(joinedload(Article.summary)).get(article_id)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    from app.services.telegram_notifier import send_article
    success = await send_article(article, db)
    if not success:
        raise HTTPException(500, "Error al enviar a Telegram")
    return {"message": "Enviado", "article_id": article_id}


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
    avg_score = None
    scored = [a.relevance_score for a in articles if a.relevance_score is not None]
    if scored:
        avg_score = round(sum(scored) / len(scored), 1)

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
# KEYWORDS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/keywords", response_model=list[KeywordOut])
def list_keywords(db: Session = Depends(get_db)):
    return db.query(Keyword).order_by(Keyword.keyword).all()


@router.post("/keywords", response_model=KeywordOut, status_code=201)
def create_keyword(body: KeywordCreate, db: Session = Depends(get_db)):
    existing = db.query(Keyword).filter(Keyword.keyword == body.keyword).first()
    if existing:
        raise HTTPException(409, f"Keyword '{body.keyword}' ya existe")
    kw = Keyword(keyword=body.keyword)
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


@router.patch("/keywords/{keyword_id}/toggle", response_model=KeywordOut)
def toggle_keyword(keyword_id: int, db: Session = Depends(get_db)):
    kw = db.query(Keyword).get(keyword_id)
    if not kw:
        raise HTTPException(404, "Keyword no encontrada")
    kw.is_active = not kw.is_active
    db.commit()
    db.refresh(kw)
    return kw


@router.delete("/keywords/{keyword_id}")
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    kw = db.query(Keyword).get(keyword_id)
    if not kw:
        raise HTTPException(404, "Keyword no encontrada")
    db.delete(kw)
    db.commit()
    return {"message": "Keyword eliminada"}


# ═══════════════════════════════════════════════════════════════════════════
# DIGEST CONFIG
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/digest/config", response_model=DigestConfigOut)
def get_digest_config(db: Session = Depends(get_db)):
    from app.config import settings
    cfg = db.query(DigestConfig).first()
    if not cfg:
        cfg = DigestConfig(hour=settings.digest_hour)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.patch("/digest/config", response_model=DigestConfigOut)
def update_digest_config(body: DigestConfigUpdate, db: Session = Depends(get_db)):
    from app.config import settings
    cfg = db.query(DigestConfig).first()
    if not cfg:
        cfg = DigestConfig(hour=settings.digest_hour)
        db.add(cfg)
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(cfg, field, val)
    cfg.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cfg)
    if body.hour is not None:
        from app.scheduler.jobs import reschedule_digest
        reschedule_digest(cfg.hour)
    return cfg


# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL ACTIONS
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/fetch/now")
@limiter.limit("10/minute")
async def fetch_now(request: Request, db: Session = Depends(get_db)):
    from app.services.rss_fetcher import fetch_all_rss
    from app.services.newsapi_fetcher import fetch_all_newsapi
    from app.services.web_scraper import fetch_all_scrapers
    rss = await fetch_all_rss(db)
    newsapi = await fetch_all_newsapi(db)
    scraped = await fetch_all_scrapers(db)
    total = rss + newsapi + scraped

    # Push notification + broadcast WS
    if total > 0:
        from app.services.notification_service import push
        from app.api.websocket import manager
        push(db, "fetch", "Fetch completado", f"{total} artículos nuevos obtenidos")
        await manager.broadcast("fetch_complete", {"total_new": total})

    return {"rss_new": rss, "newsapi_new": newsapi, "scraper_new": scraped, "total_new": total}


@router.post("/summarize/now")
@limiter.limit("10/minute")
async def summarize_now(request: Request, limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    from app.services.summarizer import summarize_pending
    count = await summarize_pending(db, limit=limit)
    return {"summarized": count}


@router.post("/digest/now")
@limiter.limit("10/minute")
async def digest_now(request: Request, db: Session = Depends(get_db)):
    from app.services.telegram_notifier import send_digest
    cfg = db.query(DigestConfig).first()
    count = cfg.count if cfg else 10
    min_score = cfg.min_score if cfg else 0

    query = (
        db.query(Article)
        .options(joinedload(Article.summary))
        .filter(Article.status.in_(["approved", "pending"]))
    )
    if min_score > 0:
        query = query.filter(
            (Article.relevance_score == None) | (Article.relevance_score >= min_score)
        )
    articles = query.order_by(Article.fetched_at.desc()).limit(count).all()
    success = await send_digest(articles)
    if not success:
        raise HTTPException(500, "Error al enviar digest a Telegram")

    from app.services.notification_service import push
    push(db, "digest", "Digest enviado", f"{len(articles)} artículos enviados por Telegram")
    return {"message": "Digest enviado", "articles_count": len(articles)}


@router.get("/digest/pdf")
async def digest_pdf(
    limit: int = Query(10, ge=1, le=50),
    min_score: int = Query(0, ge=0, le=10),
    category: str | None = None,
    db: Session = Depends(get_db),
):
    from app.services.pdf_generator import generate_digest_pdf
    query = (
        db.query(Article)
        .options(joinedload(Article.summary), joinedload(Article.source))
        .filter(Article.status.in_(["approved", "pending", "sent"]))
    )
    if min_score > 0:
        query = query.filter(
            (Article.relevance_score == None) | (Article.relevance_score >= min_score)
        )
    if category:
        query = query.filter(Article.category == category)
    articles = query.order_by(Article.fetched_at.desc()).limit(limit).all()

    pdf_bytes = generate_digest_pdf(articles)
    filename = f"newslet_digest_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ═══════════════════════════════════════════════════════════════════════════
# STATS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total       = db.query(func.count(Article.id)).scalar()
    pending     = db.query(func.count(Article.id)).filter(Article.status == "pending").scalar()
    approved    = db.query(func.count(Article.id)).filter(Article.status == "approved").scalar()
    rejected    = db.query(func.count(Article.id)).filter(Article.status == "rejected").scalar()
    sent        = db.query(func.count(Article.id)).filter(Article.status == "sent").scalar()
    sources     = db.query(func.count(Source.id)).scalar()
    keywords    = db.query(func.count(Keyword.id)).scalar()
    with_summary = db.query(func.count(Article.id)).join(Summary).scalar()
    with_cat     = db.query(func.count(Article.id)).filter(Article.category != None).scalar()
    avg_score    = db.query(func.avg(Article.relevance_score)).filter(Article.relevance_score != None).scalar()
    unread       = db.query(func.count(Notification.id)).filter(Notification.read == False).scalar()
    return StatsOut(
        total_articles=total, pending=pending, approved=approved,
        rejected=rejected, sent=sent, total_sources=sources,
        total_keywords=keywords, articles_with_summary=with_summary,
        articles_with_category=with_cat,
        avg_score=round(float(avg_score), 1) if avg_score else None,
        unread_notifications=unread,
    )


@router.get("/stats/chart")
def get_chart_stats(days: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=days)

    daily = (
        db.query(cast(Article.fetched_at, Date).label("day"), func.count(Article.id).label("count"))
        .filter(Article.fetched_at >= cutoff)
        .group_by("day").order_by("day").all()
    )
    categories = (
        db.query(Article.category, func.count(Article.id).label("count"))
        .filter(Article.category != None)
        .group_by(Article.category)
        .order_by(func.count(Article.id).desc()).all()
    )
    sentiments = (
        db.query(Article.sentiment, func.count(Article.id).label("count"))
        .filter(Article.sentiment != None)
        .group_by(Article.sentiment).all()
    )
    avg_score = db.query(func.avg(Article.relevance_score)).filter(Article.relevance_score != None).scalar()

    return {
        "daily":      [{"day": str(r.day), "count": r.count} for r in daily],
        "categories": [{"category": r.category, "count": r.count} for r in categories],
        "sentiments": [{"sentiment": r.sentiment, "count": r.count} for r in sentiments],
        "days":       days,
        "avg_score":  round(float(avg_score), 1) if avg_score else None,
    }


@router.get("/stats/heatmap", response_model=HeatmapOut)
def get_heatmap(db: Session = Depends(get_db)):
    """Activity heatmap: articles per hour of day and per weekday."""
    day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    # Per hour (0–23)
    hour_rows = (
        db.query(
            extract("hour", Article.fetched_at).label("h"),
            func.count(Article.id).label("c")
        )
        .group_by("h").all()
    )
    hour_map = {int(r.h): r.c for r in hour_rows}
    hours = [HeatmapHourPoint(hour=h, count=hour_map.get(h, 0)) for h in range(24)]

    # Per weekday (SQLite: strftime %w → 0=Sun, 1=Mon … 6=Sat)
    day_rows = (
        db.query(
            func.strftime("%w", Article.fetched_at).label("d"),
            func.count(Article.id).label("c")
        )
        .group_by("d").all()
    )
    # Convert SQLite %w (0=Sun) to Mon-first index
    sqlite_to_mon = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
    day_map: dict[int, int] = {}
    for r in day_rows:
        idx = sqlite_to_mon.get(int(r.d), 0)
        day_map[idx] = r.c

    days_out = [
        HeatmapDayPoint(day=i, day_name=day_names[i], count=day_map.get(i, 0))
        for i in range(7)
    ]
    return HeatmapOut(hours=hours, days=days_out)


@router.get("/stats/trending", response_model=TrendingOut)
def get_trending(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(15, ge=5, le=50),
    db: Session = Depends(get_db),
):
    """Extract most frequent words from recent article titles."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    rows = db.query(Article.title).filter(Article.fetched_at >= cutoff).all()

    word_re = re.compile(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]{4,}", re.UNICODE)
    counter: Counter = Counter()
    for (title,) in rows:
        words = word_re.findall(title.lower())
        counter.update(w for w in words if w not in _STOPWORDS)

    topics = [TrendingTopic(word=w, count=c) for w, c in counter.most_common(limit)]
    return TrendingOut(topics=topics, window_hours=hours)


# ═══════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Notification)
    if unread_only:
        query = query.filter(Notification.read == False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.read == False).update({"read": True})
    db.commit()
    return {"message": "Todas marcadas como leídas"}


@router.patch("/notifications/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db)):
    n = db.query(Notification).get(notification_id)
    if not n:
        raise HTTPException(404, "Notificación no encontrada")
    n.read = True
    db.commit()
    return {"message": "Marcada como leída"}


@router.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    n = db.query(Notification).get(notification_id)
    if not n:
        raise HTTPException(404, "Notificación no encontrada")
    db.delete(n)
    db.commit()
    return {"message": "Notificación eliminada"}


@router.delete("/notifications")
def clear_all_notifications(db: Session = Depends(get_db)):
    db.query(Notification).delete()
    db.commit()
    return {"message": "Historial de notificaciones limpiado"}


# ═══════════════════════════════════════════════════════════════════════════
# WEBHOOKS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/webhooks", response_model=list[WebhookOut])
def list_webhooks(db: Session = Depends(get_db)):
    return db.query(Webhook).order_by(Webhook.created_at.desc()).all()


@router.post("/webhooks", response_model=WebhookOut, status_code=201)
def create_webhook(body: WebhookCreate, db: Session = Depends(get_db)):
    wh = Webhook(name=body.name, url=body.url, events=body.events, secret=body.secret)
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


@router.patch("/webhooks/{webhook_id}/toggle", response_model=WebhookOut)
def toggle_webhook(webhook_id: int, db: Session = Depends(get_db)):
    wh = db.query(Webhook).get(webhook_id)
    if not wh:
        raise HTTPException(404, "Webhook no encontrado")
    wh.is_active = not wh.is_active
    db.commit()
    db.refresh(wh)
    return wh


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    wh = db.query(Webhook).get(webhook_id)
    if not wh:
        raise HTTPException(404, "Webhook no encontrado")
    db.delete(wh)
    db.commit()
    return {"message": "Webhook eliminado"}


# ═══════════════════════════════════════════════════════════════════════════
# RSS FEED OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/feed/rss")
def rss_feed(
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    request: Request = None,
):
    articles = (
        db.query(Article)
        .options(joinedload(Article.summary), joinedload(Article.source))
        .filter(Article.status.in_(["approved", "sent"]))
        .order_by(Article.fetched_at.desc())
        .limit(limit)
        .all()
    )
    base_url = str(request.base_url).rstrip("/") if request else "http://localhost:8000"
    from app.services.rss_generator import generate_rss_feed
    xml_content = generate_rss_feed(articles, base_url)
    return Response(content=xml_content, media_type="application/rss+xml; charset=utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/categories")
def get_categories():
    return {"categories": VALID_CATEGORIES}


# ═══════════════════════════════════════════════════════════════════════════
# AUTH (JWT — enabled only when ADMIN_PASSWORD is set)
# ═══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel as _BaseModel


class _LoginBody(_BaseModel):
    password: str


@router.post("/auth/login")
def auth_login(body: _LoginBody):
    from app.services.auth import check_password, create_token, is_auth_enabled
    if not is_auth_enabled():
        return {"token": None, "message": "Auth disabled — set ADMIN_PASSWORD in .env to enable"}
    if not check_password(body.password):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    token = create_token()
    return {"token": token, "expires_in": f"{settings.jwt_expire_minutes}m"}


@router.get("/auth/status")
def auth_status():
    from app.services.auth import is_auth_enabled
    return {"auth_enabled": is_auth_enabled()}


# ═══════════════════════════════════════════════════════════════════════════
# ARTICLE FEEDBACK
# ═══════════════════════════════════════════════════════════════════════════

class _FeedbackBody(_BaseModel):
    value: int  # -1 = dislike, 0 = reset, 1 = like


@router.post("/articles/{article_id}/feedback")
def set_article_feedback(
    article_id: int,
    body: _FeedbackBody,
    db: Session = Depends(get_db),
):
    if body.value not in (-1, 0, 1):
        raise HTTPException(400, "value must be -1, 0, or 1")
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    article.feedback = body.value
    db.commit()
    return {"id": article_id, "feedback": article.feedback}


# ═══════════════════════════════════════════════════════════════════════════
# CLUSTERS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/clusters")
def get_clusters(db: Session = Depends(get_db)):
    """Return articles grouped by cluster_id."""
    from sqlalchemy import func as _func
    rows = (
        db.query(Article.cluster_id, _func.count(Article.id).label("count"))
        .filter(Article.cluster_id != None)
        .group_by(Article.cluster_id)
        .order_by(_func.count(Article.id).desc())
        .all()
    )
    clusters = []
    for cluster_id, count in rows:
        sample = (
            db.query(Article.title)
            .filter(Article.cluster_id == cluster_id)
            .order_by(Article.relevance_score.desc())
            .limit(3)
            .all()
        )
        clusters.append({
            "cluster_id": cluster_id,
            "count": count,
            "top_titles": [t for (t,) in sample],
        })
    return {"clusters": clusters}


@router.post("/clusters/run")
async def run_clustering(db: Session = Depends(get_db)):
    """Trigger topic clustering manually."""
    from app.services.topic_clusterer import cluster_articles
    count = await cluster_articles(db)
    return {"clustered": count}


# ═══════════════════════════════════════════════════════════════════════════
# EMAIL DIGEST
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/digest/email")
async def send_email_digest(db: Session = Depends(get_db)):
    """Send today's digest via email (requires SMTP settings in .env)."""
    from app.services.email_notifier import send_email_digest as _send
    from app.models import DigestConfig
    cfg = db.query(DigestConfig).first()
    count = cfg.count if cfg else 10
    articles = (
        db.query(Article)
        .options(joinedload(Article.summary), joinedload(Article.source))
        .filter(Article.status.in_(["approved", "sent", "pending"]))
        .order_by(Article.relevance_score.desc(), Article.fetched_at.desc())
        .limit(count)
        .all()
    )
    try:
        result = await _send(articles)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


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
# ADMIN SETTINGS — read/write .env from the panel
# ═══════════════════════════════════════════════════════════════════════════

from pathlib import Path as _Path
import re as _re

_ENV_PATH = _Path(".env")

# Fields that are shown/editable from the panel (value is masked in GET if True)
_EDITABLE_FIELDS = {
    # key                     (label,                         masked, restart_needed)
    "AI_PROVIDER":            ("Proveedor IA",                False,  True),
    "GROQ_API_KEY":           ("Groq API Key",                True,   True),
    "GROQ_MODEL":             ("Groq Model",                  False,  True),
    "OPENAI_API_KEY":         ("OpenAI API Key",              True,   True),
    "OPENAI_MODEL":           ("OpenAI Model",                False,  True),
    "NEWSAPI_KEY":            ("NewsAPI Key",                 True,   True),
    "TELEGRAM_BOT_TOKEN":     ("Telegram Bot Token",          True,   True),
    "TELEGRAM_CHAT_ID":       ("Telegram Chat ID",            False,  True),
    "ADMIN_PASSWORD":         ("Contraseña del panel",        True,   True),
    "JWT_SECRET":             ("JWT Secret",                  True,   True),
    "JWT_EXPIRE_MINUTES":     ("Expiración JWT (minutos)",    False,  False),
    "SMTP_ENABLED":           ("Email habilitado",            False,  False),
    "SMTP_HOST":              ("SMTP Host",                   False,  True),
    "SMTP_PORT":              ("SMTP Puerto",                 False,  True),
    "SMTP_USER":              ("SMTP Usuario",                False,  True),
    "SMTP_PASSWORD":          ("SMTP Contraseña",             True,   True),
    "SMTP_FROM":              ("Email remitente",             False,  True),
    "SMTP_TO":                ("Email destinatario(s)",       False,  True),
    "FETCH_INTERVAL_MINUTES": ("Frecuencia fetch (minutos)",  False,  False),
    "DIGEST_HOUR":            ("Hora del digest (0-23)",      False,  False),
    "RELEVANCE_THRESHOLD":    ("Score mínimo auto-aprobar",   False,  False),
    "ENRICH_ARTICLES":        ("Enriquecer con IA",           False,  False),
    "SCRAPE_FULL_TEXT":       ("Scraping texto completo",     False,  False),
    "SOURCE_MAX_FAILURES":    ("Fallos antes de desactivar",  False,  False),
    "RATE_LIMIT_PER_MINUTE":  ("Rate limit (req/min)",        False,  False),
    "PANEL_PIN":              ("PIN del panel (alternativo)", True,   True),
}


def _read_env() -> dict[str, str]:
    """Parse .env into a dict of key→value."""
    result = {}
    if not _ENV_PATH.exists():
        return result
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _write_env(updates: dict[str, str]) -> None:
    """Write key=value pairs into .env, preserving comments and ordering."""
    if not _ENV_PATH.exists():
        content = ""
    else:
        content = _ENV_PATH.read_text(encoding="utf-8")

    lines = content.splitlines(keepends=True)
    updated_keys = set()

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}\n")
                updated_keys.add(k)
                continue
        new_lines.append(line)

    # Append any keys that weren't already in the file
    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"\n{k}={v}\n")

    _ENV_PATH.write_text("".join(new_lines), encoding="utf-8")


@router.get("/admin/settings")
def get_admin_settings():
    """Read current .env settings (secrets are masked)."""
    env = _read_env()
    result = {}
    for key, (label, masked, restart) in _EDITABLE_FIELDS.items():
        raw_val = env.get(key, "")
        result[key] = {
            "label": label,
            "value": "••••••••" if (masked and raw_val) else raw_val,
            "masked": masked,
            "restart_needed": restart,
        }
    return {"settings": result}


class _SettingsUpdate(_BaseModel):
    updates: dict[str, str]


@router.post("/admin/settings")
def update_admin_settings(body: _SettingsUpdate):
    """Write settings to .env. Only whitelisted keys are accepted."""
    allowed = set(_EDITABLE_FIELDS.keys())
    rejected = [k for k in body.updates if k not in allowed]
    if rejected:
        raise HTTPException(400, f"Claves no permitidas: {rejected}")

    # Validate a few values
    for k, v in body.updates.items():
        if k in ("FETCH_INTERVAL_MINUTES", "DIGEST_HOUR", "RELEVANCE_THRESHOLD",
                 "SOURCE_MAX_FAILURES", "JWT_EXPIRE_MINUTES", "RATE_LIMIT_PER_MINUTE",
                 "SMTP_PORT"):
            if v and not v.lstrip("-").isdigit():
                raise HTTPException(400, f"{k} debe ser un número")

    _write_env(body.updates)
    needs_restart = any(
        _EDITABLE_FIELDS[k][2] for k in body.updates if k in _EDITABLE_FIELDS
    )
    return {
        "saved": list(body.updates.keys()),
        "restart_needed": needs_restart,
        "message": (
            "✅ Guardado. Reinicia el servidor para aplicar cambios marcados como 'requiere reinicio'."
            if needs_restart else "✅ Guardado."
        ),
    }
