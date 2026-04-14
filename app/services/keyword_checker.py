"""Checks new articles against user-configured keywords and sends Telegram alerts."""
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Article, Keyword

logger = logging.getLogger(__name__)


async def check_keywords(article: Article, db: Session) -> list[str]:
    """
    Check if an article matches any active keyword.
    Sends Telegram alert if matched. Returns list of matched keywords.
    """
    keywords = db.query(Keyword).filter(Keyword.is_active == True).all()
    if not keywords:
        return []

    title_lower = (article.title or "").lower()
    text_lower = ((article.original_text or "") + " " + (article.full_text or "")).lower()
    search_text = title_lower + " " + text_lower

    matched = [kw.keyword for kw in keywords if kw.keyword.lower() in search_text]

    if matched:
        from app.services.telegram_notifier import _esc, send_message
        labels = ", ".join(f"<code>{_esc(k)}</code>" for k in matched)
        score_txt = f" · Score: <b>{article.relevance_score}/10</b>" if article.relevance_score else ""
        cat_txt = f" · {_esc(article.category)}" if article.category else ""

        text = (
            f"🔔 <b>Alerta de keyword:</b> {labels}\n\n"
            f"<b>{_esc(article.title)}</b>{score_txt}{cat_txt}\n\n"
            f'<a href="{article.url}">Leer artículo</a>'
        )
        await send_message(settings.telegram_chat_id, text)
        logger.info(f"Keyword alert sent for article {article.id}: {matched}")

    return matched


async def run_keyword_checks(articles: list[Article], db: Session) -> int:
    """Run keyword checks on a list of articles. Returns total match count."""
    total = 0
    for article in articles:
        matched = await check_keywords(article, db)
        total += len(matched)
    return total
