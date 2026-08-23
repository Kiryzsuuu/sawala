"""F3 - Avatar vs. real person (liveness) detection.

Multi-layer approach per the design doc:
  L1 Blink detection      - real faces blink, static photos/avatars don't
  L2 Micro-movement       - natural head/pose jitter across frames
  L3 Texture analysis     - photo/avatar surfaces show different noise/edge
                            statistics than real skin
  L4 Depth heuristic      - flat 2D content (avatar/photo) has low local
                            contrast gradient variance vs a real face

DeepFace-based deep liveness is optional (heavy dependency); when
unavailable we fall back to L1-L4 heuristics only (still >= 2 layers,
matching the doc's "3+ metode" recommendation as closely as dependencies
allow).
"""
from __future__ import annotations

from collections import deque

import cv2
import numpy as np
import mediapipe as mp

from src.utils.config import CONFIG
from src.utils.geometry import average_ear
from src.utils.logger import get_logger

logger = get_logger(__name__)

_face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=CONFIG.face_detection.min_detection_confidence,
    min_tracking_confidence=CONFIG.face_detection.min_tracking_confidence,
)

BLINK_EAR_THRESHOLD = 0.21


class LivenessTracker:
    """Keeps a short rolling history per participant to evaluate blink and
    micro-movement across frames (a single frame can't reveal either)."""

    def __init__(self, history_len: int = 15):
        self.ear_history: deque[float] = deque(maxlen=history_len)
        self.nose_history: deque[tuple[float, float]] = deque(maxlen=history_len)

    def update(self, tile_image: np.ndarray) -> dict:
        h, w = tile_image.shape[:2]
        rgb = cv2.cvtColor(tile_image, cv2.COLOR_BGR2RGB)
        result = _face_mesh.process(rgb)

        if not result.multi_face_landmarks:
            return {
                "is_real_person": False,
                "liveness_score": 0.0,
                "avatar_flag": True,
                "reason": "no_face_landmarks",
            }

        landmarks = result.multi_face_landmarks[0].landmark
        ear = average_ear(landmarks, w, h)
        nose = landmarks[1]
        self.ear_history.append(ear)
        self.nose_history.append((nose.x * w, nose.y * h))

        blink_detected = self._detect_blink()
        movement_detected = self._detect_micro_movement()
        texture_score = self._texture_score(tile_image)
        depth_score = self._depth_heuristic(tile_image)

        liveness_score = float(np.clip(
            0.30 * blink_detected
            + 0.25 * movement_detected
            + 0.25 * texture_score
            + 0.20 * depth_score,
            0.0,
            1.0,
        ))

        votes = sum([
            blink_detected > 0,
            movement_detected > 0,
            liveness_score > 0.6,
        ])
        is_real = votes >= 2

        return {
            "is_real_person": is_real,
            "liveness_score": round(liveness_score, 3),
            "avatar_flag": not is_real,
            "blink_detected": bool(blink_detected),
            "movement_detected": bool(movement_detected),
        }

    def _detect_blink(self) -> float:
        if len(self.ear_history) < 3:
            return 0.0
        ears = list(self.ear_history)
        dips = sum(1 for e in ears if e < BLINK_EAR_THRESHOLD)
        return 1.0 if dips >= 1 and dips < len(ears) else 0.0

    def _detect_micro_movement(self) -> float:
        if len(self.nose_history) < 5:
            return 0.0
        pts = np.array(self.nose_history)
        movement = np.std(pts, axis=0).sum()
        # Real faces show small but nonzero jitter; a static image has ~0
        return 1.0 if 0.15 < movement < 15.0 else 0.0

    @staticmethod
    def _texture_score(tile_image: np.ndarray) -> float:
        gray = cv2.cvtColor(tile_image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        # Real webcam feeds carry sensor noise/detail; overly smooth
        # (avatar) or overly sharp (photo moire) both score low.
        score = np.exp(-((laplacian_var - 150) ** 2) / (2 * 120 ** 2))
        return float(np.clip(score, 0.0, 1.0))

    @staticmethod
    def _depth_heuristic(tile_image: np.ndarray) -> float:
        gray = cv2.cvtColor(tile_image, cv2.COLOR_BGR2GRAY)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
        grad_mag = np.sqrt(gx ** 2 + gy ** 2)
        variance = float(grad_mag.var())
        score = np.clip(variance / 4000.0, 0.0, 1.0)
        return float(score)
