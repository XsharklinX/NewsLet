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


async def send_article(article: Article, db: Session) -> bool:
    """Send a single article summary to Telegram and update status to 'sent'."""
    summary_text = article.summary.summary_text if article.summary else "Sin resumen disponible."

    # Use HTML parse mode - much simpler escaping
    message = (
        f"<b>{_esc(article.title)}</b>\n\n"
        f"{_esc(summary_text)}\n\n"
        f'<a href="{article.url}">Leer mas</a>'
    )

    success = await send_message(settings.telegram_chat_id, message)
    if success:
        article.status = "sent"
        db.commit()
        logger.info(f"Sent article {article.id} to Telegram")
    return success


async def send_digest(articles: list[Article]) -> bool:
    """Send a daily digest with multiple article summaries."""
    if not articles:
        return await send_message(settings.telegram_chat_id, "<b>Digest del dia</b>\n\nNo hay noticias nuevas hoy.")

    lines = ["<b>Digest del dia</b>\n"]
    for i, article in enumerate(articles, 1):
        summary = article.summary.summary_text if article.summary else "Sin resumen."
        lines.append(f"<b>{i}. {_esc(article.title)}</b>")
        lines.append(f"{_esc(summary)}")
        lines.append(f'<a href="{article.url}">Leer</a>\n')

    message = "\n".join(lines)
    if len(message) > 4000:
        message = message[:3997] + "..."

    return await send_message(settings.telegram_chat_id, message)


def _esc(text: str) -> str:
    """Escape HTML special characters for Telegram HTML mode."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
