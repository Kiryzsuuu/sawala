"""AR-style desktop overlay: a transparent, always-on-top, click-through
window drawn directly over the real screen, showing a box + status label
above each detected participant's tile position in Zoom/Meet - no need to
switch to the SAWALA dashboard tab to see who's fatigued, off-camera, or
holding a phone.

Windows only (uses ctypes/user32 for the click-through window style).
Only meaningful together with local screen capture (Skenario B desktop
app) - the tile positions it draws come from /api/overlay-data, which is
only populated when the backend is capturing the host's own screen.
"""
from __future__ import annotations

import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
import json

POLL_INTERVAL_MS = 1000
API_URL = "http://localhost:8000/api/overlay-data"

COLOR_OK = "#2ecc71"
COLOR_ALERT = "#e74c3c"
TRANSPARENT_KEY = "#0a0a0a"  # arbitrary color unlikely to appear in real content, made transparent


def _make_click_through(window: tk.Tk) -> None:
    """Windows-only: let mouse clicks pass through to whatever's behind
    the overlay (Zoom/Meet), instead of the overlay stealing focus/clicks."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
    except Exception:
        pass  # overlay still works, just intercepts clicks on non-Windows/failure


def _fetch_overlay_data() -> list[dict]:
    try:
        with urllib.request.urlopen(API_URL, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("participants", [])
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return []


class OverlayWindow:
    """Runs on the main thread (Tkinter requirement). Toggled on/off via
    `visible` - a threading.Event so a different thread (the tray icon's
    callback thread) can flip it safely without touching Tkinter directly;
    the poll loop, already scheduled on the main thread via `.after`,
    checks it each tick."""

    def __init__(self):
        self.visible = threading.Event()

        self.root = tk.Tk()
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", TRANSPARENT_KEY)
        self.root.overrideredirect(True)  # no title bar/border
        self.root.configure(bg=TRANSPARENT_KEY)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_w}x{screen_h}+0+0")

        self.canvas = tk.Canvas(self.root, bg=TRANSPARENT_KEY, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        _make_click_through(self.root)
        self.root.withdraw()  # start hidden until toggled on
        self._poll()

    def toggle(self, show: bool | None = None) -> bool:
        """Flip (or force) visibility. Returns the new state. Safe to call
        from any thread - only sets a flag; the actual Tkinter show/hide
        happens on the next poll tick on the main thread."""
        new_state = (not self.visible.is_set()) if show is None else show
        if new_state:
            self.visible.set()
        else:
            self.visible.clear()
        return new_state

    def _poll(self):
        if self.visible.is_set():
            self.root.deiconify()
            participants = _fetch_overlay_data()
            self.canvas.delete("all")

            for p in participants:
                x, y, w, h = p["x"], p["y"], p["width"], p["height"]
                alert = p.get("fatigue_detected") or not p.get("oncam", True)
                color = COLOR_ALERT if alert else COLOR_OK

                self.canvas.create_rectangle(x, y, x + w, y + h, outline=color, width=3)

                label = p.get("name", "")
                if p.get("fatigue_detected"):
                    label += "  [Fatigue]"
                if not p.get("oncam", True):
                    label += "  [OffCam]"

                text_y = max(y - 10, 12)
                self.canvas.create_text(
                    x + 6, text_y, text=label, anchor="w",
                    fill=color, font=("Segoe UI", 11, "bold"),
                )
        else:
            self.root.withdraw()

        self.root.after(POLL_INTERVAL_MS, self._poll)

    def run(self):
        self.root.mainloop()

    def close(self):
        self.root.destroy()


def main():
    overlay = OverlayWindow()
    overlay.toggle(show=True)
    overlay.run()


if __name__ == "__main__":
    main()
