"""F5 - Fatigue detection via EAR + head pose + yawn (MAR)."""
from __future__ import annotations

from collections import deque

import cv2
import numpy as np
import mediapipe as mp

from src.utils.config import CONFIG
from src.utils.geometry import average_ear, head_pose_pitch, mouth_aspect_ratio
from src.utils.logger import get_logger

logger = get_logger(__name__)

_face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=CONFIG.face_detection.min_detection_confidence,
    min_tracking_confidence=CONFIG.face_detection.min_tracking_confidence,
)

MAR_YAWN_THRESHOLD = 0.6


class FatigueTracker:
    """Per-participant state: counts consecutive low-EAR frames and
    accumulates total fatigue duration."""

    def __init__(self, ear_threshold: float = 0.25, consecutive_frames: int = 20,
                 head_pitch_threshold_deg: float = 20.0, frame_interval_seconds: float = 3.0):
        self.ear_threshold = ear_threshold
        self.consecutive_frames = consecutive_frames
        self.head_pitch_threshold_deg = head_pitch_threshold_deg
        self.frame_interval_seconds = frame_interval_seconds

        self._low_ear_streak = 0
        self.fatigue_active = False
        self.fatigue_seconds_total = 0.0

    def update(self, tile_image: np.ndarray) -> dict:
        h, w = tile_image.shape[:2]
        rgb = cv2.cvtColor(tile_image, cv2.COLOR_BGR2RGB)
        result = _face_mesh.process(rgb)

        if not result.multi_face_landmarks:
            self._low_ear_streak = 0
            self.fatigue_active = False
            return {
                "fatigue_detected": False,
                "ear_value": None,
                "head_pitch_angle": None,
                "yawn_detected": False,
                "fatigue_duration_seconds": round(self.fatigue_seconds_total, 1),
            }

        landmarks = result.multi_face_landmarks[0].landmark
        ear = average_ear(landmarks, w, h)
        pitch = head_pose_pitch(landmarks, w, h)
        mar = mouth_aspect_ratio(landmarks, w, h)
        yawn = mar > MAR_YAWN_THRESHOLD

        if ear < self.ear_threshold:
            self._low_ear_streak += 1
        else:
            self._low_ear_streak = 0

        eyes_fatigued = self._low_ear_streak >= self.consecutive_frames
        head_down = pitch > self.head_pitch_threshold_deg
        fatigue_detected = eyes_fatigued or (head_down and ear < self.ear_threshold * 1.2) or yawn

        if fatigue_detected:
            self.fatigue_seconds_total += self.frame_interval_seconds
        self.fatigue_active = fatigue_detected

        return {
            "fatigue_detected": fatigue_detected,
            "ear_value": round(ear, 3),
            "head_pitch_angle": round(pitch, 1),
            "yawn_detected": yawn,
            "fatigue_duration_seconds": round(self.fatigue_seconds_total, 1),
        }
