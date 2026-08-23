"""Builds an annotated JPEG preview of the last captured frame, so the host
can see exactly what region is being captured and how it's being split into
tiles, instead of running the system "blind"."""
from __future__ import annotations

import cv2
import numpy as np

PREVIEW_MAX_WIDTH = 1000
JPEG_QUALITY = 70

COLOR_CONFIRMED = (0, 160, 0)     # green (BGR) - tracked as a real participant
COLOR_UNCONFIRMED = (140, 140, 140)  # gray - tile seen but no face confirmed yet


def build_preview_jpeg(frame: np.ndarray, tiles, confirmed_indices: set[int]) -> bytes:
    annotated = frame.copy()

    for tile in tiles:
        x, y, w, h = tile.bbox
        confirmed = tile.index in confirmed_indices
        color = COLOR_CONFIRMED if confirmed else COLOR_UNCONFIRMED
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        label = f"#{tile.index + 1}" + (" OK" if confirmed else " ?")
        cv2.putText(
            annotated, label, (x + 6, y + 22),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA,
        )

    h, w = annotated.shape[:2]
    if w > PREVIEW_MAX_WIDTH:
        scale = PREVIEW_MAX_WIDTH / w
        annotated = cv2.resize(annotated, (PREVIEW_MAX_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)

    ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise RuntimeError("Failed to encode preview JPEG")
    return buf.tobytes()
