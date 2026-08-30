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


THUMB_SIZE = (200, 150)
THUMBS_PER_ROW = 5


def build_named_preview_jpeg(frames: dict[str, tuple[np.ndarray, bool]]) -> bytes:
    """Mosaic preview for the named-frame pipeline (bot-fed participants),
    which has no single full gallery frame to annotate like
    build_preview_jpeg() does - each participant only ever sends their own
    already-cropped frame. `frames` maps participant name -> (last frame,
    oncam) so the host can see what the bot's pipeline sees per participant,
    same green/gray convention as the tile preview."""
    if not frames:
        raise ValueError("No frames to build a preview from")

    thumb_w, thumb_h = THUMB_SIZE
    names = sorted(frames.keys())
    rows = (len(names) + THUMBS_PER_ROW - 1) // THUMBS_PER_ROW
    cols = min(len(names), THUMBS_PER_ROW)

    canvas = np.full((rows * thumb_h, cols * thumb_w, 3), 30, dtype=np.uint8)

    for i, name in enumerate(names):
        frame, oncam = frames[name]
        color = COLOR_CONFIRMED if oncam else COLOR_UNCONFIRMED
        thumb = cv2.resize(frame, THUMB_SIZE, interpolation=cv2.INTER_AREA)
        cv2.rectangle(thumb, (0, 0), (thumb_w - 1, thumb_h - 1), color, 3)

        label = name if len(name) <= 22 else name[:19] + "..."
        (text_w, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(thumb, (0, thumb_h - 20), (min(thumb_w, text_w + 10), thumb_h), (0, 0, 0), -1)
        cv2.putText(thumb, label, (4, thumb_h - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        r, c = divmod(i, THUMBS_PER_ROW)
        canvas[r * thumb_h : (r + 1) * thumb_h, c * thumb_w : (c + 1) * thumb_w] = thumb

    ok, buf = cv2.imencode(".jpg", canvas, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not ok:
        raise RuntimeError("Failed to encode preview JPEG")
    return buf.tobytes()
