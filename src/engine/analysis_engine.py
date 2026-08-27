"""Orchestrates the per-participant detector pipeline and persistence.

Two frame sources feed the same pipeline:
  - run_cycle(): screen-capture + tile-splitter (Skenario B), tiles keyed
    by grid position, identity unknown until named manually.
  - process_named_frame(): a source that already knows real participant
    identity per frame (e.g. a Zoom Meeting SDK bot pushing frames over
    HTTP), keyed by that stable name/id, no grid guessing involved.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from src.capture.screen_capture import ScreenCapture
from src.capture.tile_splitter import TileSplitter
from src.detection import oncam_detector, phone_detector, expression_detector, name_ocr
from src.data.database import Database
from src.data.models import ParticipantStatus
from src.engine.frame_buffer import FrameBuffer, SlotKey
from src.engine.preview import build_preview_jpeg
from src.utils.config import CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisEngine:
    def __init__(self, db: Database):
        self.db = db
        # Local screen capture (mss) needs a real display - it's created
        # lazily on first use, not here, so the engine still starts fine
        # on a headless server that only ever receives frames pushed by a
        # browser (see process_screen_frame / process_named_frame) instead
        # of grabbing the host's own screen (run_cycle).
        self._capture: ScreenCapture | None = None
        self.splitter = TileSplitter(
            grid=CONFIG.capture.tile_grid,
            min_tile_size=CONFIG.capture.tile_min_size,
            max_tiles=CONFIG.capture.get("tile_max_count", 49),
        )
        self.buffer = FrameBuffer()
        self.session_id: str | None = None
        self.last_preview_jpeg: bytes | None = None
        # Posisi kotak tiap peserta dalam koordinat layar fisik asli, hanya
        # terisi kalau frame datang dari local screen capture (run_cycle) -
        # itu satu-satunya sumber yang koordinatnya benar-benar cocok
        # dengan layar Windows sungguhan, dipakai overlay AR. Frame dari
        # browser (getDisplayMedia) tidak punya info posisi layar asli.
        self.last_tile_screen_positions: dict[SlotKey, tuple[int, int, int, int]] = {}

    def _get_capture(self) -> ScreenCapture:
        if self._capture is None:
            self._capture = ScreenCapture()
        return self._capture

    def start_session(self) -> str:
        self.buffer.reset()
        self.session_id = self.db.start_session()
        return self.session_id

    def stop_session(self) -> None:
        if self.session_id:
            self.db.stop_session(self.session_id)
        self.session_id = None

    def set_participant_name(self, tile_index: int, name: str) -> None:
        self.buffer.set_name(tile_index, name)

    def _process_frame(self, key: SlotKey, image: np.ndarray, now_iso: str) -> ParticipantStatus | None:
        """Run the full detector pipeline for one participant's frame.
        Always registers/tracks the slot for this key (see face-confirmation
        note below)."""
        oncam_result = oncam_detector.detect_oncam(image)

        # Setiap tile yang berhasil dibelah oleh tile-splitter (artinya grid
        # gallery view valid) langsung dianggap peserta sungguhan, terlepas
        # dari wajahnya kedeteksi atau tidak di frame ini. Ini penting justru
        # supaya peserta yang OFFCAM sejak awal sesi (kamera mati / avatar /
        # foto profil) tetap tercatat dan dilaporkan sebagai OFFCAM, bukan
        # hilang begitu saja dari monitoring.
        slot = self.buffer.get_slot(key)
        flags: list[str] = []

        if oncam_result["face_found"]:
            slot.face_confirmed = True

        slot.oncam_state.update(oncam_result["oncam"])
        oncam_duration = slot.oncam_state.current_duration()

        if not oncam_result["oncam"]:
            return ParticipantStatus(
                id=slot.participant_id,
                name=slot.name,
                oncam=False,
                oncam_duration_seconds=round(oncam_duration, 1),
                last_seen=now_iso,
                flags=["OFFCAM"],
            )

        liveness_result = slot.liveness.update(image)
        if liveness_result["avatar_flag"]:
            flags.append("AVATAR")

        phone_result = phone_detector.detect_phone(
            image, confidence_threshold=CONFIG.thresholds.phone_confidence
        )
        if phone_result["holding_phone"]:
            flags.append("HOLDING_PHONE")

        fatigue_result = slot.fatigue.update(image)
        if fatigue_result["fatigue_detected"]:
            flags.append("FATIGUE")

        expression_result = expression_detector.detect_expression(
            image, smile_confidence_threshold=CONFIG.thresholds.smile_confidence
        )
        if expression_result["smiling"]:
            flags.append("ENGAGED")

        return ParticipantStatus(
            id=slot.participant_id,
            name=slot.name,
            oncam=True,
            oncam_duration_seconds=round(oncam_duration, 1),
            is_real_person=liveness_result["is_real_person"],
            liveness_score=liveness_result["liveness_score"],
            avatar_flag=liveness_result["avatar_flag"],
            holding_phone=phone_result["holding_phone"],
            phone_confidence=phone_result["phone_confidence"],
            fatigue_detected=fatigue_result["fatigue_detected"],
            ear_value=fatigue_result["ear_value"],
            head_pitch_angle=fatigue_result["head_pitch_angle"],
            fatigue_duration_seconds=fatigue_result["fatigue_duration_seconds"],
            smiling=expression_result["smiling"],
            smile_confidence=expression_result["smile_confidence"],
            dominant_emotion=expression_result["dominant_emotion"],
            last_seen=now_iso,
            flags=flags,
        )

    def process_screen_frame(
        self, frame: np.ndarray, screen_offset: tuple[int, int] | None = None
    ) -> list[ParticipantStatus]:
        """Split one full gallery-view frame into tiles and run the full
        pipeline on each (Skenario B), regardless of where the frame came
        from: local ScreenCapture.grab() (run_cycle) or a browser upload
        via getDisplayMedia (the /api/ingest/screen endpoint, used when
        the backend runs somewhere without local display access, e.g. a
        cloud deployment). Persists and returns the statuses for this tick.

        `screen_offset` is the (left, top) of the captured region in real
        physical screen coordinates - only known for local capture, since
        a browser-captured frame's on-screen position isn't knowable from
        here. When given, tile positions are recorded for the AR overlay."""
        if not self.session_id:
            raise RuntimeError("No active session - call start_session() first")

        tiles = self.splitter.split(frame)
        now_iso = datetime.now(timezone.utc).isoformat()
        statuses: list[ParticipantStatus] = []

        if screen_offset is not None:
            self.last_tile_screen_positions = {}
        offset_x, offset_y = screen_offset or (0, 0)

        for tile in tiles:
            status = self._process_frame(tile.index, tile.image, now_iso)
            if status is not None:
                if self.buffer.is_unresolved_name(tile.index):
                    x, y, w, h = tile.bbox
                    ocr_name = name_ocr.read_tile_name(frame[y : y + h, x : x + w])
                    if ocr_name:
                        self.buffer.set_ocr_name(tile.index, ocr_name)
                        status.name = ocr_name
                statuses.append(status)
                if screen_offset is not None:
                    x, y, w, h = tile.bbox
                    self.last_tile_screen_positions[tile.index] = (x + offset_x, y + offset_y, w, h)

        for status in statuses:
            self.db.insert_snapshot(self.session_id, status)

        confirmed_indices = {
            tile.index for tile in tiles
            if (slot := self.buffer.peek_slot(tile.index)) is not None and slot.face_confirmed
        }
        self.last_preview_jpeg = build_preview_jpeg(frame, tiles, confirmed_indices)

        return statuses

    def run_cycle(self) -> list[ParticipantStatus]:
        """Perform one capture+analyze+persist cycle from local screen
        capture (Skenario B, desktop app). Returns the list of participant
        statuses for this tick."""
        if not self.session_id:
            raise RuntimeError("No active session - call start_session() first")
        capture = self._get_capture()
        frame = capture.grab()
        offset = (capture.region["left"], capture.region["top"])
        return self.process_screen_frame(frame, screen_offset=offset)

    def overlay_data(self) -> list[dict]:
        """Current confirmed participants with their on-screen tile
        position, for the AR overlay window. Only meaningful when the
        last cycle came from local screen capture (run_cycle)."""
        results = []
        for key, pos in self.last_tile_screen_positions.items():
            slot = self.buffer.peek_slot(key)
            if slot is None:
                continue
            x, y, w, h = pos
            results.append({
                "participant_id": slot.participant_id,
                "name": slot.name,
                "x": x, "y": y, "width": w, "height": h,
                "oncam": slot.oncam_state.oncam,
                "fatigue_detected": slot.fatigue.fatigue_active,
            })
        return results

    def capture_preview(self) -> bytes:
        """Grab one frame and return an annotated preview JPEG showing the
        capture region and current tile split, without requiring an active
        session or running the full detection pipeline. Lets the host
        calibrate `capture.region` / `capture.tile_grid` before or during
        monitoring, instead of running blind."""
        frame = self._get_capture().grab()
        tiles = self.splitter.split(frame)
        faces_now = {
            tile.index for tile in tiles
            if oncam_detector.detect_oncam(tile.image)["face_found"]
        }
        self.last_preview_jpeg = build_preview_jpeg(frame, tiles, faces_now)
        return self.last_preview_jpeg

    def process_named_frame(self, participant_name: str, image: np.ndarray) -> ParticipantStatus | None:
        """Analyze one frame already attributed to a real participant name
        (pushed by an external bot, e.g. a Zoom Meeting SDK bot), and
        persist + return the resulting status. Returns None if the session
        isn't active or the participant isn't confirmed yet."""
        if not self.session_id:
            raise RuntimeError("No active session - call start_session() first")

        now_iso = datetime.now(timezone.utc).isoformat()
        status = self._process_frame(participant_name, image, now_iso)
        if status is not None:
            self.db.insert_snapshot(self.session_id, status)
        return status

    def snapshot_all(self) -> list[ParticipantStatus]:
        """Current status of every confirmed participant, regardless of
        which frame source last updated them. Used to broadcast a full
        picture after an external (bot-pushed) frame updates just one
        participant."""
        statuses = []
        for slot in self.buffer.active_slots():
            duration = slot.oncam_state.current_duration()
            statuses.append(ParticipantStatus(
                id=slot.participant_id,
                name=slot.name,
                oncam=slot.oncam_state.oncam,
                oncam_duration_seconds=round(duration, 1),
                fatigue_duration_seconds=round(slot.fatigue.fatigue_seconds_total, 1),
                fatigue_detected=slot.fatigue.fatigue_active,
            ))
        return statuses

    def close(self) -> None:
        if self._capture is not None:
            self._capture.close()
