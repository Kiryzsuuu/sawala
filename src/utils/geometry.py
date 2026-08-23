"""Geometry helpers: EAR, MAR, head pose, mouth curve - used by fatigue &
expression detectors. All functions operate on MediaPipe FaceMesh landmarks
(normalized x, y in [0, 1] relative to the tile image) plus tile width/height
to get pixel coordinates.
"""
from __future__ import annotations

import numpy as np

# MediaPipe FaceMesh landmark indices (468-point model)
LEFT_EYE = [33, 160, 158, 133, 153, 144]     # p1..p6 order for EAR formula
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
MOUTH_CORNERS = (61, 291)          # left, right mouth corner
MOUTH_TOP_BOTTOM = (13, 14)        # upper lip / lower lip (inner)
MOUTH_VERTICAL_OUTER = (0, 17)     # for MAR (top / bottom outer)
NOSE_TIP = 1
CHIN = 152
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263
LEFT_MOUTH = 61
RIGHT_MOUTH = 291


def _to_px(landmarks, idx: int, w: int, h: int) -> np.ndarray:
    lm = landmarks[idx]
    return np.array([lm.x * w, lm.y * h])


def eye_aspect_ratio(landmarks, w: int, h: int, eye_indices: list[int]) -> float:
    """EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)"""
    p1, p2, p3, p4, p5, p6 = [_to_px(landmarks, i, w, h) for i in eye_indices]
    vertical = np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)
    horizontal = 2.0 * np.linalg.norm(p1 - p4)
    if horizontal == 0:
        return 0.0
    return float(vertical / horizontal)


def average_ear(landmarks, w: int, h: int) -> float:
    left = eye_aspect_ratio(landmarks, w, h, LEFT_EYE)
    right = eye_aspect_ratio(landmarks, w, h, RIGHT_EYE)
    return (left + right) / 2.0


def mouth_aspect_ratio(landmarks, w: int, h: int) -> float:
    """MAR - mulut terbuka lebar (yawn) jika tinggi. Analog EAR untuk mulut."""
    top = _to_px(landmarks, MOUTH_VERTICAL_OUTER[0], w, h)
    bottom = _to_px(landmarks, MOUTH_VERTICAL_OUTER[1], w, h)
    left = _to_px(landmarks, LEFT_MOUTH, w, h)
    right = _to_px(landmarks, RIGHT_MOUTH, w, h)
    vertical = np.linalg.norm(top - bottom)
    horizontal = np.linalg.norm(left - right)
    if horizontal == 0:
        return 0.0
    return float(vertical / horizontal)


def mouth_curve_ratio(landmarks, w: int, h: int) -> float:
    """Perkiraan senyum: rasio jarak sudut mulut terhadap lebar wajah, dan
    posisi sudut mulut relatif terhadap garis tengah bibir (naik = senyum)."""
    left = _to_px(landmarks, LEFT_MOUTH, w, h)
    right = _to_px(landmarks, RIGHT_MOUTH, w, h)
    top = _to_px(landmarks, MOUTH_VERTICAL_OUTER[0], w, h)
    bottom = _to_px(landmarks, MOUTH_VERTICAL_OUTER[1], w, h)
    mouth_center_y = (top[1] + bottom[1]) / 2.0
    corner_avg_y = (left[1] + right[1]) / 2.0
    # Sudut mulut lebih tinggi (y lebih kecil) dari titik tengah -> tersenyum
    lift = mouth_center_y - corner_avg_y
    width = np.linalg.norm(left - right)
    if width == 0:
        return 0.0
    return float(lift / width)


def head_pose_pitch(landmarks, w: int, h: int) -> float:
    """Estimasi kasar sudut pitch kepala (derajat) dari posisi vertikal
    hidung relatif terhadap garis mata dan dagu. Positif = menunduk.
    Ini bukan solvePnP penuh, melainkan heuristik ringan yang cukup untuk
    flag fatigue tanpa kalibrasi kamera.
    """
    nose = _to_px(landmarks, NOSE_TIP, w, h)
    chin = _to_px(landmarks, CHIN, w, h)
    left_eye = _to_px(landmarks, LEFT_EYE_OUTER, w, h)
    right_eye = _to_px(landmarks, RIGHT_EYE_OUTER, w, h)
    eye_mid = (left_eye + right_eye) / 2.0

    face_height = np.linalg.norm(chin - eye_mid)
    if face_height == 0:
        return 0.0

    nose_to_eye = nose[1] - eye_mid[1]
    ratio = nose_to_eye / face_height
    # ratio ~0.35 saat pandangan lurus (empiris); makin besar -> menunduk
    baseline = 0.35
    pitch_deg = (ratio - baseline) * 90.0
    return float(max(0.0, pitch_deg))
