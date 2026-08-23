"""F1/F2 - OnCam/OffCam detection + duration tracking."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import cv2
import numpy as np
import mediapipe as mp

from src.utils.config import CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)

_face_detector = mp.solutions.face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=CONFIG.face_detection.min_detection_confidence,
)

BLACK_TILE_THRESHOLD = 15.0  # mean intensity below this => treated as black/offcam


@dataclass
class OnCamState:
    """Per-participant running state for oncam duration bookkeeping."""

    oncam: bool = False
    oncam_seconds_total: float = 0.0
    last_transition_ts: float = field(default_factory=time.time)
    last_seen_ts: float = field(default_factory=time.time)

    def update(self, is_oncam: bool, now: float | None = None) -> None:
        now = now or time.time()
        if is_oncam and not self.oncam:
            self.last_transition_ts = now
        elif not is_oncam and self.oncam:
            self.oncam_seconds_total += now - self.last_transition_ts
        elif is_oncam and self.oncam:
            pass  # still accumulating, finalized on next offcam or snapshot
        self.oncam = is_oncam
        self.last_seen_ts = now

    def current_duration(self, now: float | None = None) -> float:
        now = now or time.time()
        if self.oncam:
            return self.oncam_seconds_total + (now - self.last_transition_ts)
        return self.oncam_seconds_total


def has_video_feed(tile_image: np.ndarray) -> bool:
    """Cheap pre-check: an offcam tile (black screen or a static name-avatar
    background) tends to have very low variance / low mean intensity."""
    gray = cv2.cvtColor(tile_image, cv2.COLOR_BGR2GRAY)
    mean_intensity = float(gray.mean())
    std_intensity = float(gray.std())
    if mean_intensity < BLACK_TILE_THRESHOLD and std_intensity < 10:
        return False
    return True


def detect_oncam(tile_image: np.ndarray) -> dict:
    """Returns detection result for a single tile: whether a face (primary
    oncam indicator) was found, and whether the tile even carries a live
    video feed at all."""
    feed_present = has_video_feed(tile_image)
    face_found = False
    if feed_present:
        rgb = cv2.cvtColor(tile_image, cv2.COLOR_BGR2RGB)
        result = _face_detector.process(rgb)
        face_found = bool(result.detections)

    oncam = feed_present and (face_found or _has_skin_tone_region(tile_image))
    return {
        "feed_present": feed_present,
        "face_found": face_found,
        "oncam": oncam,
    }


def _has_skin_tone_region(tile_image: np.ndarray, min_ratio: float = 0.03) -> bool:
    """Fallback signal when the face detector misses (e.g. angled face):
    presence of a meaningful skin-tone colored region."""
    ycrcb = cv2.cvtColor(tile_image, cv2.COLOR_BGR2YCrCb)
    lower = np.array([0, 133, 77], dtype=np.uint8)
    upper = np.array([255, 173, 127], dtype=np.uint8)
    mask = cv2.inRange(ycrcb, lower, upper)
    ratio = float(np.count_nonzero(mask)) / mask.size
    return ratio >= min_ratio
