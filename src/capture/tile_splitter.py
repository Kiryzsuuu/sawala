"""Splits a gallery-view screenshot into per-participant tiles.

Two modes:
  - explicit grid ("2x2", "3x3", "4x4", ...): even split by rows/cols
  - "auto": detect tile boundaries via contour/edge analysis on the dark
    gutters that most conferencing UIs render between tiles.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)

TARGET_SIZE = (224, 224)


@dataclass
class Tile:
    index: int
    image: np.ndarray          # resized to TARGET_SIZE, BGR
    bbox: tuple[int, int, int, int]   # x, y, w, h in original frame


class TileSplitter:
    def __init__(self, grid: str = "auto", min_tile_size: int = 80, max_tiles: int = 49):
        self.grid = grid
        self.min_tile_size = min_tile_size
        self.max_tiles = max_tiles

    def split(self, frame: np.ndarray) -> list[Tile]:
        if self.grid == "auto":
            boxes = self._auto_detect_grid(frame)
        else:
            boxes = self._fixed_grid(frame, self.grid)

        if len(boxes) > self.max_tiles:
            logger.warning(
                "Auto grid detected %d tiles, exceeds max_tiles=%d (layar yang di-capture "
                "kemungkinan bukan gallery view meeting) - fallback ke 1 tile penuh",
                len(boxes), self.max_tiles,
            )
            boxes = self._fixed_grid(frame, "1x1")

        tiles = []
        for i, (x, y, w, h) in enumerate(boxes):
            if w < self.min_tile_size or h < self.min_tile_size:
                continue
            crop = frame[y : y + h, x : x + w]
            resized = cv2.resize(crop, TARGET_SIZE, interpolation=cv2.INTER_AREA)
            tiles.append(Tile(index=i, image=resized, bbox=(x, y, w, h)))
        return tiles

    def _fixed_grid(self, frame: np.ndarray, grid: str) -> list[tuple[int, int, int, int]]:
        match = re.match(r"(\d+)x(\d+)", grid)
        if not match:
            raise ValueError(f"Invalid grid spec: {grid}")
        cols, rows = int(match.group(1)), int(match.group(2))
        h, w = frame.shape[:2]
        tile_w, tile_h = w // cols, h // rows
        boxes = []
        for r in range(rows):
            for c in range(cols):
                boxes.append((c * tile_w, r * tile_h, tile_w, tile_h))
        return boxes

    def _auto_detect_grid(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Detect near-uniform-color gutters (typically black/dark gray in
        Zoom/Meet/Teams gallery views) to infer the tile grid, then falls
        back to treating the whole frame as a single tile if no gutters are
        found (e.g. only one participant, so there's nothing to gutter
        against).
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Row/col profiles: mean intensity per row/col - gutters show up as
        # narrow bands of near-constant low intensity.
        row_profile = gray.mean(axis=1)
        col_profile = gray.mean(axis=0)

        row_splits = self._find_splits(row_profile)
        col_splits = self._find_splits(col_profile)

        if len(row_splits) >= 1 and len(col_splits) >= 1:
            row_bounds = [0] + row_splits + [h]
            col_bounds = [0] + col_splits + [w]
            boxes = []
            for i in range(len(row_bounds) - 1):
                for j in range(len(col_bounds) - 1):
                    y0, y1 = row_bounds[i], row_bounds[i + 1]
                    x0, x1 = col_bounds[j], col_bounds[j + 1]
                    boxes.append((x0, y0, x1 - x0, y1 - y0))
            logger.debug("Auto grid detected: %d rows x %d cols", len(row_bounds) - 1, len(col_bounds) - 1)
            return boxes

        # No gutters found - most likely a single participant (nothing
        # adjacent to create a gutter against), so treat the whole frame as
        # one tile rather than fabricating a fixed grid that would slice one
        # real face into several fake "participants".
        logger.debug("Auto grid detection found no gutters, treating frame as a single tile")
        return self._fixed_grid(frame, "1x1")

    @staticmethod
    def _find_splits(profile: np.ndarray, dark_thresh: float = 40.0, min_gap: int = 12) -> list[int]:
        """Find contiguous dark bands in an intensity profile, return their
        midpoints as split coordinates. `min_gap` is deliberately wide
        (real gallery-view gutters are thick, solid bands) so that thin
        dark UI elements on a regular desktop (window borders, text,
        icons) are not mistaken for tile boundaries."""
        dark = profile < dark_thresh
        splits = []
        i = 0
        n = len(dark)
        while i < n:
            if dark[i]:
                start = i
                while i < n and dark[i]:
                    i += 1
                if i - start >= min_gap and 0 < start < n - 1:
                    splits.append((start + i) // 2)
            else:
                i += 1
        return splits
