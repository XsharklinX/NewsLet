"""Validates critical dependencies on application startup."""
import logging

import httpx
from sqlalchemy import text

from app.config import settings
from app.database import engine

logger = logging.getLogger(__name__)

PLACEHOLDER_VALUES = {"", "your-key-here", "sk-your-key-here", "gsk_your-key-here", "your-bot-token-here"}


def _is_set(value: str) -> bool:
    return bool(value) and value not in PLACEHOLDER_VALUES


async def validate_startup() -> dict[str, bool]:
    """Run all startup checks. Returns dict of {check_name: passed}."""
    results: dict[str, bool] = {}
    logger.info("=" * 50)
    logger.info("NewsBot Pro — Startup Validation")
    logger.info("=" * 50)

    # 1. Database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        results["database"] = True
        logger.info("[OK]   Database reachable")
    except Exception as e:
        results["database"] = False
        logger.critical(f"[FAIL] Database: {e}")

    # 2. AI provider
    ai_key = settings.groq_api_key if settings.ai_provider == "groq" else settings.openai_api_key
    if _is_set(ai_key):
        results["ai_api"] = True
        logger.info(f"[OK]   AI key present ({settings.ai_provider} / {settings.groq_model if settings.ai_provider == 'groq' else settings.openai_model})")
    else:
        results["ai_api"] = False
        logger.warning(f"[WARN] AI key missing for '{settings.ai_provider}' — summarization disabled")

    # 3. Telegram bot token
    if _is_set(settings.telegram_bot_token):
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
                )
                data = resp.json()
                if data.get("ok"):
                    bot_name = data["result"].get("username", "?")
                    results["telegram"] = True
                    logger.info(f"[OK]   Telegram bot @{bot_name} connected")
                else:
                    results["telegram"] = False
                    logger.warning(f"[WARN] Telegram token invalid: {data.get('description')}")
        except Exception as e:
            results["telegram"] = False
            logger.warning(f"[WARN] Telegram unreachable: {e}")
    else:
        results["telegram"] = False
        logger.warning("[WARN] Telegram not configured — notifications disabled")

    # 4. Telegram chat ID
    if _is_set(settings.telegram_chat_id):
        results["telegram_chat"] = True
        logger.info(f"[OK]   Telegram chat_id: {settings.telegram_chat_id}")
    else:
        results["telegram_chat"] = False
        logger.warning("[WARN] Telegram chat_id not set — bot won't know where to send messages")

    # 5. NewsAPI (optional)
    if _is_set(settings.newsapi_key):
        results["newsapi"] = True
        logger.info("[OK]   NewsAPI key present")
    else:
        results["newsapi"] = False
        logger.info("[INFO] NewsAPI key not configured (optional — RSS still works)")

    logger.info("=" * 50)
    passed = sum(results.values())
    logger.info(f"Startup: {passed}/{len(results)} checks passed")
    logger.info("=" * 50)
    return results
