"""F6 - Smile / expression detection.

Primary metric: mouth curve ratio from FaceMesh landmarks (always available,
no extra dependency). DeepFace is used opportunistically for the richer
`dominant_emotion` breakdown when installed; otherwise emotion falls back to
a simple 3-way classification (happy / neutral / other) derived from the
same mouth-curve signal.
"""
from __future__ import annotations

import cv2
import numpy as np
import mediapipe as mp

from src.utils.config import CONFIG
from src.utils.geometry import mouth_curve_ratio
from src.utils.logger import get_logger

logger = get_logger(__name__)

_face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=CONFIG.face_detection.min_detection_confidence,
    min_tracking_confidence=CONFIG.face_detection.min_tracking_confidence,
)

try:
    from deepface import DeepFace

    _DEEPFACE_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _DEEPFACE_AVAILABLE = False
    logger.warning("DeepFace not available - expression detection running in mouth-curve-only mode")


def detect_expression(tile_image: np.ndarray, smile_confidence_threshold: float = 0.6) -> dict:
    h, w = tile_image.shape[:2]
    rgb = cv2.cvtColor(tile_image, cv2.COLOR_BGR2RGB)
    result = _face_mesh.process(rgb)

    if not result.multi_face_landmarks:
        return {
            "smiling": False,
            "smile_confidence": 0.0,
            "dominant_emotion": "unknown",
            "emotion_scores": {},
        }

    landmarks = result.multi_face_landmarks[0].landmark
    curve = mouth_curve_ratio(landmarks, w, h)
    # Map curve ratio (typically ~[-0.05, 0.15]) to a 0-1 confidence.
    smile_confidence = float(np.clip((curve + 0.02) / 0.12, 0.0, 1.0))
    smiling = smile_confidence >= smile_confidence_threshold

    if _DEEPFACE_AVAILABLE:
        try:
            analysis = DeepFace.analyze(
                tile_image, actions=["emotion"], enforce_detection=False, silent=True
            )
            if isinstance(analysis, list):
                analysis = analysis[0]
            emotion_scores = {k: round(float(v) / 100.0, 3) for k, v in analysis["emotion"].items()}
            dominant_emotion = analysis["dominant_emotion"]
            return {
                "smiling": smiling,
                "smile_confidence": round(smile_confidence, 3),
                "dominant_emotion": dominant_emotion,
                "emotion_scores": emotion_scores,
            }
        except Exception as exc:  # pragma: no cover
            logger.warning("DeepFace analyze failed, falling back: %s", exc)

    dominant_emotion = "happy" if smiling else "neutral"
    emotion_scores = {
        "happy": round(smile_confidence, 3),
        "neutral": round(1.0 - smile_confidence, 3),
    }
    return {
        "smiling": smiling,
        "smile_confidence": round(smile_confidence, 3),
        "dominant_emotion": dominant_emotion,
        "emotion_scores": emotion_scores,
    }
