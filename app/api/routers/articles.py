import io
import csv
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Article
from app.schemas.article import ArticleListOut, ArticleOut, ArticleStatusUpdate
from app.services.auth import require_auth

from pydantic import BaseModel as _BaseModel

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_auth)],
)


class _FeedbackBody(_BaseModel):
    value: int  # -1 = dislike, 0 = reset, 1 = like


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
