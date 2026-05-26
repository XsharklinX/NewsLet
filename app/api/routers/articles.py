import io
import csv
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Article
from app.schemas.article import (
    ArticleListOut, ArticleOut, ArticleStatusUpdate, ArticleShortlistUpdate
)
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
    shortlisted: bool | None = None,
    source_id: int | None = None,
    category: str | None = None,
    sentiment: str | None = None,
    tag: str | None = Query(None, max_length=100),
    min_score: int | None = Query(None, ge=1, le=10),
    search: str | None = Query(None, max_length=200),
    date_from: str | None = Query(None, description="ISO datetime — only articles fetched after this"),
    date_to:   str | None = Query(None, description="ISO datetime — only articles fetched before this"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Article).options(joinedload(Article.summary), joinedload(Article.source))
    if status:
        query = query.filter(Article.status == status)
    if shortlisted is not None:
        query = query.filter(Article.is_shortlisted == shortlisted)
    if source_id:
        query = query.filter(Article.source_id == source_id)
    if category:
        query = query.filter(Article.category == category)
    if sentiment:
        query = query.filter(Article.sentiment == sentiment)
    if tag:
        query = query.filter(Article.tags.ilike(f"%{tag}%"))
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
    if date_to:
        try:
            from datetime import datetime as _dt
            ceiling = _dt.fromisoformat(date_to.replace("Z", "+00:00")).replace(tzinfo=None)
            query = query.filter(Article.fetched_at <= ceiling)
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


@router.get("/articles/export/markdown")
def export_articles_markdown(
    status: str | None = None,
    category: str | None = None,
    min_score: int | None = Query(None, ge=1, le=10),
    count: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Export filtered articles as a Markdown digest."""
    query = db.query(Article).options(joinedload(Article.summary), joinedload(Article.source))
    if status:
        query = query.filter(Article.status == status)
    if category:
        query = query.filter(Article.category == category)
    if min_score is not None:
        query = query.filter(Article.relevance_score >= min_score)

    articles = query.order_by(Article.fetched_at.desc()).limit(count).all()

    lines = [
        "# Digest NewsLet Pro",
        "",
        f"_Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}_",
        "",
        "---",
        "",
    ]
    for i, a in enumerate(articles, 1):
        score_str = f" · ⭐ {a.relevance_score}/10" if a.relevance_score else ""
        cat_str   = f" · {a.category}" if a.category else ""
        src_str   = a.source.name if a.source else ""
        lines.append(f"## {i}. {a.title}")
        lines.append("")
        lines.append(f"**Fuente:** {src_str}{cat_str}{score_str}")
        lines.append("")
        if a.summary:
            lines.append(a.summary.summary_text)
            lines.append("")
            if a.summary.key_point:
                lines.append(f"**Punto clave:** {a.summary.key_point}")
                lines.append("")
        lines.append(f"[Leer artículo completo]({a.url})")
        lines.append("")
        lines.append("---")
        lines.append("")

    filename = f"newslet_digest_{datetime.now().strftime('%Y%m%d')}.md"
    return Response(
        content="\n".join(lines).encode("utf-8"),
        media_type="text/markdown",
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


@router.get("/articles/{article_id}/related")
def related_articles(article_id: int, db: Session = Depends(get_db)):
    """Return up to 5 articles related by cluster or category (excluding self)."""
    article = db.query(Article).get(article_id)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")

    cutoff = datetime.utcnow() - timedelta(days=14)
    base_query = (
        db.query(Article)
        .options(joinedload(Article.summary), joinedload(Article.source))
        .filter(
            Article.id != article_id,
            Article.fetched_at >= cutoff,
        )
    )
    
    related = []
    # 1. Prioritize Cluster
    if article.cluster_id:
        related = base_query.filter(Article.cluster_id == article.cluster_id).limit(5).all()
    
    # 2. Fallback to Category
    if not related and article.category:
        related = base_query.filter(Article.category == article.category).order_by(Article.relevance_score.desc().nulls_last()).limit(5).all()

    return {"articles": related}


@router.patch("/articles/{article_id}/status", response_model=ArticleOut)
def update_article_status(article_id: int, body: ArticleStatusUpdate, db: Session = Depends(get_db)):
    article = db.query(Article).get(article_id)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    article.status = body.status
    db.commit()
    db.refresh(article)
    return article


@router.patch("/articles/{article_id}/shortlist", response_model=ArticleOut)
def update_article_shortlist(article_id: int, body: ArticleShortlistUpdate, db: Session = Depends(get_db)):
    article = db.query(Article).get(article_id)
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    article.is_shortlisted = body.is_shortlisted
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


# ═══════════════════════════════════════════════════════════════════════════
# TAGS (Tier 1.4)
# ═══════════════════════════════════════════════════════════════════════════

class _TagsBody(_BaseModel):
    tags: list[str]


@router.get("/tags")
def list_all_tags(db: Session = Depends(get_db)):
    """Return all unique tags used across articles."""
    from sqlalchemy import text as _text
    rows = db.execute(_text(
        "SELECT DISTINCT tags FROM articles WHERE tags IS NOT NULL AND tags != ''"
    )).fetchall()
    tag_set: set[str] = set()
    for (tags_str,) in rows:
        for t in tags_str.split(","):
            t = t.strip()
            if t:
                tag_set.add(t)
    return {"tags": sorted(tag_set)}


@router.patch("/articles/{article_id}/tags")
def update_article_tags(article_id: int, body: _TagsBody, db: Session = Depends(get_db)):
    """Set tags for an article (replaces existing tags)."""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(404, "Artículo no encontrado")
    tags = list(dict.fromkeys(t.strip().lower() for t in body.tags if t.strip()))
    article.tags = ",".join(tags)
    db.commit()
    return {"id": article_id, "tags": tags}
