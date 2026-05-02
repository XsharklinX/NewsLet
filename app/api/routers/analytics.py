import re
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, Date, func, extract
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article, Keyword, Source, Summary
from app.models.notification import Notification
from app.schemas.article import (
    HeatmapOut, HeatmapHourPoint, HeatmapDayPoint,
    StatsOut, TrendingOut, TrendingTopic,
)
from app.services.auth import require_auth

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_auth)],
)

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


@router.get("/logs")
def get_logs(lines: int = Query(100, ge=10, le=500)):
    """Return the last N lines from the application log file."""
    from pathlib import Path
    from app.config import settings

    log_path = Path(settings.log_file)
    if not log_path.exists():
        return {"lines": [], "path": str(log_path)}

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        tail = [l.rstrip() for l in all_lines[-lines:] if l.strip()]
        return {"lines": tail, "total": len(all_lines), "path": str(log_path)}
    except Exception as e:
        return {"lines": [f"Error reading log: {e}"], "total": 0, "path": str(log_path)}


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Detailed health check for the panel status indicator."""
    from app.scheduler.jobs import scheduler
    checks = {}

    # DB connectivity
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Scheduler
    checks["scheduler"] = "ok" if scheduler.running else "stopped"

    # Article counts
    from app.models import Article, Source
    checks["articles_total"]  = db.query(Article).count()
    checks["sources_active"]  = db.query(Source).filter(Source.is_active == True).count()
    checks["sources_disabled"] = db.query(Source).filter(Source.is_active == False).count()

    # Config warnings
    from app.config import settings
    warnings = []
    if not settings.groq_api_key and not settings.openai_api_key:
        warnings.append("Sin API key de IA (GROQ_API_KEY o OPENAI_API_KEY)")
    if not settings.telegram_bot_token:
        warnings.append("Sin TELEGRAM_BOT_TOKEN — notificaciones desactivadas")
    if checks["sources_active"] == 0:
        warnings.append("No hay fuentes activas — no se obtendrán noticias")
    checks["warnings"] = warnings

    all_ok = all(v == "ok" for k, v in checks.items() if isinstance(v, str))
    return {"status": "ok" if all_ok else "degraded", "checks": checks, "warnings": warnings}


@router.get("/stats/ai-usage")
def ai_usage_stats(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    """Token consumption per day + total cost estimate."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    daily = (
        db.query(
            cast(Summary.created_at, Date).label("day"),
            func.sum(Summary.tokens_used).label("tokens"),
            func.count(Summary.id).label("count"),
        )
        .filter(Summary.created_at >= cutoff)
        .group_by("day").order_by("day").all()
    )
    total_tokens = db.query(func.sum(Summary.tokens_used)).scalar() or 0
    total_count  = db.query(func.count(Summary.id)).scalar() or 0
    # Groq Llama 3.3 70B: $0.59/1M tokens (blended); rough estimate
    cost_usd = round(float(total_tokens) * 0.00000059, 4)
    return {
        "daily":              [{"day": str(r.day), "tokens": r.tokens or 0, "count": r.count} for r in daily],
        "total_tokens":       total_tokens,
        "total_summaries":    total_count,
        "estimated_cost_usd": cost_usd,
        "days":               days,
    }
