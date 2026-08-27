"""Reads the participant display-name label baked into a gallery-view tile
via OCR (Tesseract), so tiles don't stay stuck as generic "Participant N"
when the host hasn't manually named them.

Best-effort only: conferencing UIs vary a lot in where/how they render the
name label, so a miss here just leaves the slot with its current name -
manual naming via /api/participants/name always takes precedence and is
never overwritten.
"""
from __future__ import annotations

import re

import cv2
import numpy as np

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None

from src.utils.config import CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)

_INVALID_CHARS = re.compile(r"[^A-Za-z0-9 .'-]")
_WARNED_MISSING_TESSERACT = False


def _ocr_config() -> dict:
    node = CONFIG.get("ocr")
    return node._raw if node is not None else {}


def _ocr_enabled() -> bool:
    return bool(_ocr_config().get("enabled", True))


def read_tile_name(tile_crop: np.ndarray) -> str | None:
    """Try to OCR the name label from the bottom strip of a gallery-view
    tile crop (pass the original, un-resized crop - the 224x224 detector
    input is too downsampled for text to survive). Returns None if
    pytesseract isn't installed, OCR is disabled, or no confident text was
    found."""
    global _WARNED_MISSING_TESSERACT

    if not _ocr_enabled():
        return None

    if pytesseract is None:
        if not _WARNED_MISSING_TESSERACT:
            logger.warning(
                "pytesseract tidak terinstal - auto-naming peserta via OCR dimatikan "
                "(pasang `pip install pytesseract` + Tesseract-OCR binary untuk mengaktifkan)"
            )
            _WARNED_MISSING_TESSERACT = True
        return None

    ocr_config = _ocr_config()
    strip_ratio = ocr_config.get("name_strip_ratio", 0.16)
    min_confidence = ocr_config.get("min_confidence", 60)

    h, w = tile_crop.shape[:2]
    strip_h = max(int(h * strip_ratio), 16)
    strip = tile_crop[h - strip_h : h, :]

    gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
    scale = 3
    gray = cv2.resize(gray, (w * scale, strip_h * scale), interpolation=cv2.INTER_CUBIC)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    try:
        data = pytesseract.image_to_data(
            binary, output_type=pytesseract.Output.DICT, config="--psm 7"
        )
    except pytesseract.TesseractNotFoundError:
        if not _WARNED_MISSING_TESSERACT:
            logger.warning(
                "Binary Tesseract-OCR tidak ditemukan di PATH - auto-naming peserta via OCR "
                "dimatikan (pasang Tesseract-OCR dari sistem, bukan cuma pip package-nya)"
            )
            _WARNED_MISSING_TESSERACT = True
        return None

    words: list[str] = []
    confidences: list[float] = []
    for text, conf in zip(data["text"], data["conf"]):
        text = text.strip()
        if not text:
            continue
        try:
            conf = float(conf)
        except ValueError:
            continue
        if conf < 0:
            continue
        words.append(text)
        confidences.append(conf)

    if not words:
        return None

    avg_confidence = sum(confidences) / len(confidences)
    if avg_confidence < min_confidence:
        return None

    name = _INVALID_CHARS.sub("", " ".join(words)).strip()
    if len(name) < 2:
        return None
    return name
