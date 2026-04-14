"""
Webhook dispatcher: fires HTTP POST to registered URLs on system events.
Supports HMAC-SHA256 signing with a secret.
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

VALID_EVENTS = {"fetch", "keyword", "digest", "article_high_score", "error"}


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


async def fire_webhooks(event: str, data: dict, db) -> int:
    """
    Fire all active webhooks subscribed to this event.
    Returns number of successfully delivered webhooks.
    """
    from app.models.webhook import Webhook

    webhooks = (
        db.query(Webhook)
        .filter(Webhook.is_active == True)
        .all()
    )

    subscribed = [
        wh for wh in webhooks
        if event in (wh.events or "").split(",")
    ]

    if not subscribed:
        return 0

    payload_dict = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    payload_str = json.dumps(payload_dict, ensure_ascii=False)

    delivered = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for wh in subscribed:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "NewsLet-Webhook/3.0",
                "X-NewsLet-Event": event,
            }
            if wh.secret:
                sig = _sign(payload_str, wh.secret)
                headers["X-NewsLet-Signature"] = f"sha256={sig}"

            try:
                resp = await client.post(wh.url, content=payload_str, headers=headers)
                resp.raise_for_status()
                wh.last_fired_at = datetime.utcnow()
                db.commit()
                delivered += 1
                logger.info(f"Webhook delivered to {wh.url} [{resp.status_code}]")
            except Exception as e:
                logger.warning(f"Webhook failed for {wh.url}: {e}")

    return delivered
