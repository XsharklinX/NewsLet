import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.limiter import limiter
from app.models import Article, DigestConfig
from app.services.auth import require_auth

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_auth)],
)


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


@router.post("/digest/email")
async def send_email_digest(db: Session = Depends(get_db)):
    """Send today's digest via email (requires SMTP settings in .env)."""
    from app.services.email_notifier import send_email_digest as _send
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
