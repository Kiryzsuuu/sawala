"""REST endpoints per section 8, plus a frame-ingest endpoint for external
bot sources (e.g. a Zoom Meeting SDK bot pushing named per-participant
frames instead of the host screen-capturing gallery view)."""
from __future__ import annotations

import socket
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel

from src.api.bot_manager import bot_manager
from src.api.websocket import manager
from src.auth.security import decode_access_token
from src.data.exporter import export_csv, export_json
from src.data.models import SessionInfo
from src.utils.config import CONFIG


def _authorize_ingest(x_ingest_token: str | None, authorization: str | None) -> None:
    """Endpoint ingest bisa dipanggil bot eksternal (X-Ingest-Token) atau
    tombol "Aktifkan Screen Capture" di dashboard (Authorization: Bearer
    dari user yang sudah login) - keduanya sah, salah satu cukup."""
    expected_token = CONFIG.bot_ingest.get("token")
    if expected_token and expected_token != "change-me" and x_ingest_token == expected_token:
        return

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if decode_access_token(token):
            return

    raise HTTPException(401, "Perlu login atau X-Ingest-Token yang valid")


_LOOPBACK_ADDRESSES = {"127.0.0.1", "::1"}


def _is_loopback_request(request: Request) -> bool:
    return bool(request.client) and request.client.host in _LOOPBACK_ADDRESSES


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


class BotStartRequest(BaseModel):
    join_url: str
    display_name: str = "SAWALA"
    passcode: str | None = None


def get_state(request_app):
    return request_app.state


def register_routes(app, engine, monitor_loop, get_current_user):
    @app.get("/api/network-info")
    def network_info(request: Request):
        """Link peserta dibangun dari origin request yang sebenarnya
        (bukan tebakan port dev), jadi otomatis benar baik saat diakses
        dari desktop app (:8000), LAN (IP host), maupun production di
        belakang Nginx (domain publik, port 443/80 tersirat)."""
        forwarded_proto = request.headers.get("x-forwarded-proto")
        scheme = forwarded_proto or request.url.scheme
        host = request.headers.get("host") or request.url.netloc
        participant_link = f"{scheme}://{host}/?view=saya"

        return {
            "lan_ip": _detect_lan_ip(),
            "participant_link": participant_link,
        }

    @app.get("/api/overlay-data")
    def get_overlay_data(request: Request, authorization: str | None = Header(default=None)):
        """Posisi layar tiap peserta yang terkonfirmasi, untuk jendela
        overlay AR desktop. Cuma terisi kalau sumber capture-nya local
        screen capture (run_cycle), bukan browser/bot. Dibuka tanpa login
        dari localhost saja (overlay jalan di mesin yang sama dengan
        server), supaya launcher desktop tidak perlu simpan kredensial."""
        if not _is_loopback_request(request):
            if not (authorization and authorization.startswith("Bearer ") and decode_access_token(
                authorization.removeprefix("Bearer ").strip()
            )):
                raise HTTPException(401, "Endpoint ini hanya untuk localhost atau user yang sudah login")
        return {"participants": engine.overlay_data()}

    @app.get("/api/preview")
    def get_preview(_: dict = Depends(get_current_user)):
        """Screenshot terakhir yang di-capture, lengkap dengan kotak tile
        yang terdeteksi (hijau = sudah terkonfirmasi jadi peserta, abu-abu
        = belum). Bisa dipanggil kapan saja, termasuk sebelum sesi dimulai,
        untuk kalibrasi region capture / grid. Hanya untuk local screen
        capture (mss) - lihat /api/preview/last untuk sumber browser."""
        try:
            jpeg = engine.capture_preview()
        except Exception as exc:
            raise HTTPException(500, f"Gagal mengambil preview: {exc}")
        return Response(content=jpeg, media_type="image/jpeg")

    @app.get("/api/preview/last")
    def get_last_preview(_: dict = Depends(get_current_user)):
        """Frame terakhir yang benar-benar diproses lewat pipeline, dengan
        kotak tile yang sama seperti /api/preview - tapi tanpa mengambil
        capture baru, jadi ini satu-satunya cara melihat preview kalau
        sumber framenya browser (/api/ingest/screen), bukan mss lokal.
        404 kalau belum ada frame yang diproses sama sekali."""
        if engine.last_preview_jpeg is None:
            raise HTTPException(404, "Belum ada frame yang diproses. Mulai sesi dan aktifkan screen capture dulu.")
        return Response(content=engine.last_preview_jpeg, media_type="image/jpeg")

    @app.get("/api/session", response_model=SessionInfo)
    def get_session(_: dict = Depends(get_current_user)):
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
    async def start_session(_: dict = Depends(get_current_user)):
        session_id = engine.start_session()
        # Di deployment tanpa akses layar lokal (mis. cloud), matikan lewat
        # capture.enable_local_capture: false di config.yaml - host memakai
        # /api/ingest/screen (tombol "Aktifkan Screen Capture" di dashboard)
        # sebagai gantinya, bukan mss lokal yang tidak akan pernah berhasil.
        if CONFIG.capture.get("enable_local_capture", True):
            monitor_loop.start()
        return {"session_id": session_id, "status": "started"}

    @app.post("/api/session/stop")
    async def stop_session(_: dict = Depends(get_current_user)):
        await monitor_loop.stop()
        engine.stop_session()
        return {"status": "stopped"}

    @app.post("/api/participants/name")
    def set_participant_name(update: ParticipantNameUpdate, _: dict = Depends(get_current_user)):
        engine.set_participant_name(update.tile_index, update.name)
        return {"status": "ok"}

    @app.post("/api/bot/start")
    def start_bot(update: BotStartRequest, _: dict = Depends(get_current_user)):
        if not engine.session_id:
            raise HTTPException(409, "Mulai sesi monitoring dulu sebelum menjalankan bot")
        # Bot jalan sebagai subprocess di mesin yang sama dengan backend ini,
        # jadi panggil lewat loopback langsung - lebih andal daripada lewat
        # domain publik/reverse proxy (yang belum tentu dikonfigurasi benar
        # untuk trafik dari proses lokal).
        api_base = f"http://127.0.0.1:{CONFIG.api.port}"
        try:
            bot_manager.start(update.join_url, update.display_name, update.passcode, api_base)
        except RuntimeError as exc:
            raise HTTPException(409, str(exc))
        return {"status": "started"}

    @app.post("/api/bot/stop")
    def stop_bot(_: dict = Depends(get_current_user)):
        bot_manager.stop()
        return {"status": "stopped"}

    @app.get("/api/bot/status")
    def bot_status(_: dict = Depends(get_current_user)):
        return bot_manager.status()

    @app.post("/api/bot/clear-log")
    def clear_bot_log(_: dict = Depends(get_current_user)):
        if bot_manager.is_running():
            raise HTTPException(409, "Hentikan bot dulu sebelum membersihkan log")
        bot_manager.clear_log()
        return {"status": "ok"}

    @app.post("/api/ingest/frame")
    async def ingest_frame(
        participant_name: str,
        file: UploadFile = File(...),
        x_ingest_token: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ):
        """Menerima satu frame per peserta dari sumber eksternal (mis. bot
        Zoom Meeting SDK), sebagai alternatif screen-capture Skenario B.
        Peserta diidentifikasi lewat nama asli, bukan tebakan posisi tile."""
        _authorize_ingest(x_ingest_token, authorization)

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

    @app.post("/api/ingest/screen")
    async def ingest_screen(
        file: UploadFile = File(...),
        x_ingest_token: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ):
        """Menerima satu screenshot gallery-view penuh dari browser host
        (lewat getDisplayMedia), sebagai alternatif screen-capture lokal
        (mss) untuk skenario deploy di cloud yang tidak punya akses layar
        lokal. Frame ini melalui pipeline yang sama persis dengan
        run_cycle(): tile-split lalu deteksi per tile."""
        _authorize_ingest(x_ingest_token, authorization)

        if not engine.session_id:
            raise HTTPException(409, "No active session - call /api/session/start first")

        raw = await file.read()
        buffer = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(400, "Could not decode image")

        statuses = engine.process_screen_frame(image)

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "participants": [s.model_dump() for s in statuses],
        }
        await manager.broadcast(payload)

        return {"status": "ok", "participants_seen": len(statuses)}

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
    def export_csv_endpoint(_: dict = Depends(get_current_user)):
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
    def export_json_endpoint(_: dict = Depends(get_current_user)):
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
