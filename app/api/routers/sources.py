import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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
