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
from src.detection import oncam_detector, phone_detector, expression_detector
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
        self.capture = ScreenCapture()
        self.splitter = TileSplitter(
            grid=CONFIG.capture.tile_grid,
            min_tile_size=CONFIG.capture.tile_min_size,
            max_tiles=CONFIG.capture.get("tile_max_count", 49),
        )
        self.buffer = FrameBuffer()
        self.session_id: str | None = None
        self.last_preview_jpeg: bytes | None = None

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
        Returns None if this key isn't confirmed yet and no face was found
        in this frame either (see face-confirmation note below)."""
        oncam_result = oncam_detector.detect_oncam(image)

        # Sebuah slot baru hanya dianggap peserta sungguhan setelah AI
        # benar-benar mendeteksi wajah di dalamnya. Ini mencegah potongan
        # UI acak (bukan gallery view meeting) tercatat sebagai "peserta
        # hantu". Slot yang sudah pernah terkonfirmasi tetap dilacak walau
        # kameranya kemudian dimatikan (offcam).
        if not oncam_result["face_found"] and not self.buffer.has_slot(key):
            return None

        slot = self.buffer.get_slot(key)
        flags: list[str] = []

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

    def run_cycle(self) -> list[ParticipantStatus]:
        """Perform one capture+analyze+persist cycle from screen capture
        (Skenario B). Returns the list of participant statuses for this
        tick."""
        if not self.session_id:
            raise RuntimeError("No active session - call start_session() first")

        frame = self.capture.grab()
        tiles = self.splitter.split(frame)
        now_iso = datetime.now(timezone.utc).isoformat()
        statuses: list[ParticipantStatus] = []

        for tile in tiles:
            status = self._process_frame(tile.index, tile.image, now_iso)
            if status is not None:
                statuses.append(status)

        for status in statuses:
            self.db.insert_snapshot(self.session_id, status)

        confirmed_indices = {tile.index for tile in tiles if self.buffer.has_slot(tile.index)}
        self.last_preview_jpeg = build_preview_jpeg(frame, tiles, confirmed_indices)

        return statuses

    def capture_preview(self) -> bytes:
        """Grab one frame and return an annotated preview JPEG showing the
        capture region and current tile split, without requiring an active
        session or running the full detection pipeline. Lets the host
        calibrate `capture.region` / `capture.tile_grid` before or during
        monitoring, instead of running blind."""
        frame = self.capture.grab()
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
        self.capture.close()
