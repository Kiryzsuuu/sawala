"""FastAPI application entry point."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import register_routes
from src.api.websocket import MonitorLoop, manager
from src.data.database import Database
from src.engine.analysis_engine import AnalysisEngine
from src.utils.config import CONFIG, PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

db = Database()
engine = AnalysisEngine(db)
monitor_loop = MonitorLoop(engine, interval_seconds=CONFIG.capture.interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SAWALA API starting up")
    yield
    await monitor_loop.stop()
    engine.close()
    db.close()
    logger.info("SAWALA API shut down")


app = FastAPI(title="SAWALA API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_routes(app, engine, monitor_loop)


@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive / ignore client pings
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/api/health")
def health():
    return {"status": "ok"}


def _dashboard_dist_dir() -> Path | None:
    """Locate the built dashboard (dashboard/dist), whether running from
    source or bundled by PyInstaller (assets live under sys._MEIPASS)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "."))
        candidate = base / "dashboard_dist"
    else:
        candidate = PROJECT_ROOT / "dashboard" / "dist"
    return candidate if candidate.is_dir() else None


_dist_dir = _dashboard_dist_dir()
if _dist_dir:
    # Mounted last so it never shadows /api/* or /ws/live above; serves the
    # built dashboard directly, so packaged builds only need this one
    # server running (no separate `npm run dev`).
    app.mount("/", StaticFiles(directory=_dist_dir, html=True), name="dashboard")
    logger.info("Serving built dashboard from %s", _dist_dir)
else:
    logger.info("No built dashboard found - run `npm run build` in dashboard/ to serve it from here")


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=CONFIG.api.host,
        port=CONFIG.api.port,
        reload=False,
    )
