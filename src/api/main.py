"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import register_routes
from src.api.websocket import MonitorLoop, manager
from src.data.database import Database
from src.engine.analysis_engine import AnalysisEngine
from src.utils.config import CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)

db = Database()
engine = AnalysisEngine(db)
monitor_loop = MonitorLoop(engine, interval_seconds=CONFIG.capture.interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Meeting Monitor API starting up")
    yield
    await monitor_loop.stop()
    engine.close()
    db.close()
    logger.info("Meeting Monitor API shut down")


app = FastAPI(title="Meeting Monitor API", version="1.0.0", lifespan=lifespan)

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


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=CONFIG.api.host,
        port=CONFIG.api.port,
        reload=False,
    )
