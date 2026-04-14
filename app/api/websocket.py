"""
WebSocket connection manager for real-time live updates.
Broadcasts events (new articles, fetch complete, etc.) to all connected clients.
"""
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self):
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._active.append(ws)
        logger.debug(f"WS connected. Total: {len(self._active)}")

    def disconnect(self, ws: WebSocket):
        self._active.remove(ws)
        logger.debug(f"WS disconnected. Total: {len(self._active)}")

    async def broadcast(self, event: str, data: Any = None):
        """Send a typed event to all connected clients."""
        payload = json.dumps({
            "event": event,
            "data": data,
            "ts": datetime.utcnow().isoformat(),
        })
        dead = []
        for ws in self._active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                self._active.remove(ws)
            except ValueError:
                pass

    @property
    def active_count(self) -> int:
        return len(self._active)


# Singleton used across the app
manager = ConnectionManager()
