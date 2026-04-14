"""
Notification service: creates in-app notifications stored in the DB.
"""
import logging

logger = logging.getLogger(__name__)

ICONS = {
    "fetch":             "🔄",
    "keyword":           "🔑",
    "digest":            "📬",
    "error":             "⚠️",
    "info":              "ℹ️",
    "article_high_score": "⭐",
}


def push(db, type_: str, title: str, message: str) -> None:
    """Create a new notification. Silently ignores errors."""
    try:
        from app.models.notification import Notification
        notif = Notification(type=type_, title=title, message=message)
        db.add(notif)
        db.commit()
    except Exception as e:
        logger.warning(f"notification_service.push failed: {e}")
