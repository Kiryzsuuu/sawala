"""F4 - Phone-holding detection.

Primary path: YOLOv8 (COCO class "cell phone") + MediaPipe Hands to confirm
a hand is near the detected phone bounding box.

`ultralytics` is a heavy optional dependency. If it isn't installed, this
module degrades gracefully: hand landmarks are still detected, and a
lightweight "hand near face, object-shaped blob" heuristic is used instead,
with a note in the result that this is a reduced-confidence fallback.
"""
from __future__ import annotations

import cv2
import numpy as np
import mediapipe as mp

from src.utils.config import CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)

_hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=CONFIG.face_detection.min_detection_confidence,
    min_tracking_confidence=CONFIG.face_detection.min_tracking_confidence,
)

try:
    from ultralytics import YOLO

    _yolo_model = YOLO("yolov8n.pt")
    _YOLO_AVAILABLE = True
    _CELL_PHONE_CLASS_ID = 67  # COCO class id for "cell phone"
except Exception:  # pragma: no cover - optional dependency
    _yolo_model = None
    _YOLO_AVAILABLE = False
    logger.warning("ultralytics/YOLO not available - phone detection running in fallback heuristic mode")


def detect_phone(tile_image: np.ndarray, confidence_threshold: float = 0.5) -> dict:
    hand_present = _detect_hand(tile_image)

    if _YOLO_AVAILABLE:
        return _detect_phone_yolo(tile_image, hand_present, confidence_threshold)
    return _detect_phone_fallback(tile_image, hand_present)


def _detect_hand(tile_image: np.ndarray) -> bool:
    rgb = cv2.cvtColor(tile_image, cv2.COLOR_BGR2RGB)
    result = _hands.process(rgb)
    return bool(result.multi_hand_landmarks)


def _detect_phone_yolo(tile_image: np.ndarray, hand_present: bool, threshold: float) -> dict:
    results = _yolo_model.predict(tile_image, verbose=False, conf=threshold)
    best_conf = 0.0
    found = False
    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == _CELL_PHONE_CLASS_ID:
                conf = float(box.conf[0])
                if conf > best_conf:
                    best_conf = conf
                    found = True

    holding_phone = found and hand_present and best_conf >= threshold
    return {
        "holding_phone": holding_phone,
        "phone_confidence": round(best_conf, 3),
        "hand_present": hand_present,
        "method": "yolov8",
    }


def _detect_phone_fallback(tile_image: np.ndarray, hand_present: bool) -> dict:
    """Heuristic fallback: rectangular, dark, high-contrast blob near/below
    a detected hand often indicates a phone in a webcam feed. Confidence is
    intentionally conservative and should be treated as advisory only."""
    if not hand_present:
        return {"holding_phone": False, "phone_confidence": 0.0, "hand_present": False, "method": "fallback_heuristic"}

    gray = cv2.cvtColor(tile_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_score = 0.0
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if area < 400:
            continue
        aspect = h / w if w else 0
        if 1.6 <= aspect <= 2.4:  # phone-like elongated rectangle
            score = min(1.0, area / (tile_image.shape[0] * tile_image.shape[1]) * 8)
            best_score = max(best_score, score)

    holding_phone = best_score >= 0.35
    return {
        "holding_phone": holding_phone,
        "phone_confidence": round(best_score, 3),
        "hand_present": True,
        "method": "fallback_heuristic",
    }
