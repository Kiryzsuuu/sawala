"""REST endpoints per section 8, plus a frame-ingest endpoint for external
bot sources (e.g. a Zoom Meeting SDK bot pushing named per-participant
frames instead of the host screen-capturing gallery view)."""
from __future__ import annotations

import socket
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import APIRouter, File, Header, HTTPException, Response, UploadFile
from pydantic import BaseModel

from src.api.websocket import manager
from src.data.exporter import export_csv, export_json
from src.data.models import SessionInfo
from src.utils.config import CONFIG


def _detect_lan_ip() -> str:
    """Best-effort LAN IP so the host can share a link participants on the
    same network can open. Doesn't actually send any traffic (UDP connect
    is just used to make the OS pick a real outbound interface)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

router = APIRouter()


class ParticipantNameUpdate(BaseModel):
    tile_index: int
    name: str


def get_state(request_app):
    return request_app.state


def register_routes(app, engine, monitor_loop):
    @app.get("/api/network-info")
    def network_info():
        lan_ip = _detect_lan_ip()
        dashboard_port = 5173
        return {
            "lan_ip": lan_ip,
            "dashboard_port": dashboard_port,
            "participant_link": f"http://{lan_ip}:{dashboard_port}/?view=saya",
        }

    @app.get("/api/preview")
    def get_preview():
        """Screenshot terakhir yang di-capture, lengkap dengan kotak tile
        yang terdeteksi (hijau = sudah terkonfirmasi jadi peserta, abu-abu
        = belum). Bisa dipanggil kapan saja, termasuk sebelum sesi dimulai,
        untuk kalibrasi region capture / grid."""
        try:
            jpeg = engine.capture_preview()
        except Exception as exc:
            raise HTTPException(500, f"Gagal mengambil preview: {exc}")
        return Response(content=jpeg, media_type="image/jpeg")

    @app.get("/api/session", response_model=SessionInfo)
    def get_session():
        row = engine.db.get_active_session()
        if not row:
            raise HTTPException(404, "No active session")
        participants = engine.db.get_participants(row["session_id"])
        return SessionInfo(
            session_id=row["session_id"],
            started_at=row["started_at"],
            active=bool(row["active"]),
            participant_count=len(participants),
        )

    @app.post("/api/session/start")
    async def start_session():
        session_id = engine.start_session()
        monitor_loop.start()
        return {"session_id": session_id, "status": "started"}

    @app.post("/api/session/stop")
    async def stop_session():
        await monitor_loop.stop()
        engine.stop_session()
        return {"status": "stopped"}

    @app.post("/api/participants/name")
    def set_participant_name(update: ParticipantNameUpdate):
        engine.set_participant_name(update.tile_index, update.name)
        return {"status": "ok"}

    @app.post("/api/ingest/frame")
    async def ingest_frame(
        participant_name: str,
        file: UploadFile = File(...),
        x_ingest_token: str | None = Header(default=None),
    ):
        """Menerima satu frame per peserta dari sumber eksternal (mis. bot
        Zoom Meeting SDK), sebagai alternatif screen-capture Skenario B.
        Peserta diidentifikasi lewat nama asli, bukan tebakan posisi tile."""
        expected_token = CONFIG.bot_ingest.get("token")
        if expected_token and expected_token != "change-me" and x_ingest_token != expected_token:
            raise HTTPException(401, "Invalid or missing X-Ingest-Token")

        if not engine.session_id:
            raise HTTPException(409, "No active session - call /api/session/start first")

        raw = await file.read()
        buffer = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(400, "Could not decode image")

        engine.process_named_frame(participant_name, image)

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "participants": [s.model_dump() for s in engine.snapshot_all()],
        }
        await manager.broadcast(payload)

        return {"status": "ok"}

    @app.get("/api/participants")
    def get_participants():
        row = engine.db.get_active_session()
        if not row:
            return {"participants": []}
        return {"participants": engine.db.get_participants(row["session_id"])}

    @app.get("/api/participants/{participant_id}")
    def get_participant(participant_id: str):
        row = engine.db.get_active_session()
        if not row:
            raise HTTPException(404, "No active session")
        history = engine.db.get_participant_history(row["session_id"], participant_id)
        if not history:
            raise HTTPException(404, "Participant not found")
        return {"participant_id": participant_id, "history": history}

    @app.get("/api/export/csv")
    def export_csv_endpoint():
        row = engine.db.get_active_session()
        if not row:
            raise HTTPException(404, "No active session")
        csv_data = export_csv(engine.db, row["session_id"])
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=session_{row['session_id']}.csv"},
        )

    @app.get("/api/export/json")
    def export_json_endpoint():
        row = engine.db.get_active_session()
        if not row:
            raise HTTPException(404, "No active session")
        json_data = export_json(engine.db, row["session_id"])
        return Response(
            content=json_data,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=session_{row['session_id']}.json"},
        )

    return router
