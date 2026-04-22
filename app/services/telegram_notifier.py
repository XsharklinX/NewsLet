import logging

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Article

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"


async def _tg(method: str, **kwargs) -> dict | None:
    """Call a Telegram Bot API method."""
    url = f"{TELEGRAM_API.format(token=settings.telegram_bot_token)}/{method}"
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(url, json=kwargs)
            data = resp.json()
            if not data.get("ok"):
                logger.error(f"Telegram {method} error: {data}")
                return None
            return data.get("result")
        except Exception as e:
            logger.error(f"Telegram {method} exception: {e}")
            return None


async def send_message(chat_id: str, text: str, parse_mode: str = "HTML", reply_markup: dict | None = None) -> bool:
    """Send a message via Telegram Bot API."""
    kwargs = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": False}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    result = await _tg("sendMessage", **kwargs)
    return result is not None


def _format_article_message(article: Article) -> str:
    """Format an article as a Telegram HTML message, using structured summary when available."""
    s = article.summary

    # Metadata line
    score_badge = f"⭐ {article.relevance_score}/10  " if article.relevance_score else ""
    cat_badge   = f"🏷 {article.category}  " if article.category else ""
    sentiment_icon = {"positive": "🟢", "negative": "🔴", "neutral": "🔵"}.get(
        article.sentiment or "", ""
    )

    meta = f"{score_badge}{cat_badge}{sentiment_icon}".strip()
    header = f"<b>{_esc(article.title)}</b>"
    if meta:
        header += f"\n<i>{meta}</i>"

    # Structured summary (new format) or plain fallback
    if s and s.key_point:
        body = (
            f"\n🎯 <b>Punto clave:</b> {_esc(s.key_point)}"
            + (f"\n📌 <b>Contexto:</b> {_esc(s.context_note)}" if s.context_note else "")
            + (f"\n💥 <b>Impacto:</b> {_esc(s.impact)}" if s.impact else "")
        )
    elif s:
        body = f"\n{_esc(s.summary_text)}"
    else:
        body = "\n<i>Sin resumen disponible.</i>"

    return f"{header}{body}\n\n<a href=\"{article.url}\">Leer artículo completo →</a>"


async def send_article(article: Article, db: Session) -> bool:
    """Send a single article summary to Telegram and update status to 'sent'."""
    message = _format_article_message(article)
    success = await send_message(settings.telegram_chat_id, message)
    if success:
        article.status = "sent"
        db.commit()
        logger.info(f"Sent article {article.id} to Telegram")
    return success


async def send_digest(articles: list[Article]) -> bool:
    """Send a daily digest with multiple article summaries."""
    if not articles:
        return await send_message(settings.telegram_chat_id, "<b>📰 Digest del día</b>\n\nNo hay noticias nuevas hoy.")

    lines = [f"<b>📰 Digest del día</b> — {len(articles)} noticias\n"]
    for i, article in enumerate(articles, 1):
        s = article.summary
        score = f" ⭐{article.relevance_score}" if article.relevance_score else ""
        lines.append(f"<b>{i}.{score} {_esc(article.title)}</b>")
        if s and s.key_point:
            lines.append(f"🎯 {_esc(s.key_point)}")
        elif s:
            snippet = s.summary_text[:150].rstrip()
            lines.append(_esc(snippet + ("..." if len(s.summary_text) > 150 else "")))
        lines.append(f'<a href="{article.url}">Leer →</a>\n')

    message = "\n".join(lines)
    if len(message) > 4000:
        message = message[:3997] + "..."

    return await send_message(settings.telegram_chat_id, message)


def _esc(text: str) -> str:
    """Escape HTML special characters for Telegram HTML mode."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
