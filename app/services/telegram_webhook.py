"""
Telegram Webhook registration.
Instead of polling (requires always-on process), Telegram pushes updates
to our HTTPS endpoint. Works perfectly with sleep-capable free hosting.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def register_webhook(base_url: str) -> bool:
    """
    Tell Telegram to send updates to our /telegram/webhook endpoint.
    base_url: the public HTTPS URL of the app (e.g. https://myapp.onrender.com)
    """
    if not settings.telegram_bot_token:
        logger.warning("Webhook: no bot token configured, skipping")
        return False

    webhook_url = f"{base_url.rstrip('/')}/api/v1/telegram/webhook"
    api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(api_url, json={
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": False,
            })
        data = resp.json()
        if data.get("ok"):
            logger.info(f"Webhook registered: {webhook_url}")
            return True
        else:
            logger.error(f"Webhook registration failed: {data}")
            return False
    except Exception as e:
        logger.error(f"Webhook registration error: {e}")
        return False


async def delete_webhook() -> bool:
    """Remove the webhook (used when switching back to polling for local dev)."""
    if not settings.telegram_bot_token:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/deleteWebhook",
                json={"drop_pending_updates": False},
            )
        return resp.json().get("ok", False)
    except Exception:
        return False


async def get_webhook_info() -> dict:
    """Get current webhook status from Telegram."""
    if not settings.telegram_bot_token:
        return {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getWebhookInfo"
            )
        return resp.json().get("result", {})
    except Exception:
        return {}
