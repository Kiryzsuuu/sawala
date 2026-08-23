"""WebSocket connection manager + background monitoring loop broadcasting
live updates per section 8's payload format."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import WebSocket

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        logger.info("WebSocket client connected (%d total)", len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)
        logger.info("WebSocket client disconnected (%d total)", len(self.active))

    async def broadcast(self, payload: dict) -> None:
        message = json.dumps(payload, default=str)
        stale = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)


manager = ConnectionManager()


class MonitorLoop:
    """Drives AnalysisEngine.run_cycle() on the configured interval and
    broadcasts each tick's results to connected dashboard clients."""

    def __init__(self, engine, interval_seconds: float):
        self.engine = engine
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            try:
                statuses = self.engine.run_cycle()
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "participants": [s.model_dump() for s in statuses],
                }
                await manager.broadcast(payload)
            except Exception as exc:
                logger.exception("Monitor loop tick failed: %s", exc)
            await asyncio.sleep(self.interval_seconds)
