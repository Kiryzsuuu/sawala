"""Screen capture using `mss` - cross-platform, fast, no GDI/X11 dependency
beyond what mss already wraps."""
from __future__ import annotations

from typing import Optional

import numpy as np
import mss

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ScreenCapture:
    def __init__(self, region: Optional[dict] = None):
        """region: {"top": int, "left": int, "width": int, "height": int} or
        None to capture the primary monitor in full."""
        self._sct = mss.mss()
        self.region = region or self._primary_monitor_region()
        logger.info("ScreenCapture initialized with region=%s", self.region)

    def _primary_monitor_region(self) -> dict:
        monitor = self._sct.monitors[1]  # index 0 = all monitors combined
        return {
            "top": monitor["top"],
            "left": monitor["left"],
            "width": monitor["width"],
            "height": monitor["height"],
        }

    def set_region(self, top: int, left: int, width: int, height: int) -> None:
        self.region = {"top": top, "left": left, "width": width, "height": height}
        logger.info("Capture region updated: %s", self.region)

    def grab(self) -> np.ndarray:
        """Return a BGR numpy array (OpenCV-compatible) of the configured region."""
        shot = self._sct.grab(self.region)
        frame = np.array(shot)  # BGRA
        return frame[:, :, :3]  # drop alpha -> BGR

    def close(self) -> None:
        self._sct.close()
