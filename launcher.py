"""Desktop launcher for Meeting Monitor.

Starts the FastAPI server (which also serves the built dashboard, see
src/api/main.py's static mount) in a background thread, opens the
dashboard in the default browser once it's ready, and shows a system tray
icon so the app behaves like an installed program rather than a bare
terminal window: click the icon to reopen the dashboard, or quit from
there to stop the server.
"""
from __future__ import annotations

import os
import sys

# A windowed (console=False) PyInstaller build has sys.stdout/stderr set to
# None, not just closed - anything that tries to write to them (uvicorn's
# own logging setup included) crashes immediately and silently, since this
# runs on a daemon thread with no visible traceback. Give them a real (if
# discarded) stream before anything else touches logging.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn
from PIL import Image
from pystray import Icon, Menu, MenuItem

from src.utils.config import CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)

DASHBOARD_URL = f"http://localhost:{CONFIG.api.port}/"
HEALTH_URL = f"http://localhost:{CONFIG.api.port}/api/health"


def _icon_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", "."))
    else:
        base = Path(__file__).resolve().parent
    return base / "app.ico"


class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        from src.api.main import app  # imported here so logging is set up first

        config = uvicorn.Config(app, host=CONFIG.api.host, port=CONFIG.api.port, log_level="info")
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def _wait_until_ready(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    return False


def main() -> None:
    logger.info("SAWALA launcher starting")
    server_thread = ServerThread()
    server_thread.start()

    if _wait_until_ready():
        webbrowser.open(DASHBOARD_URL)
    else:
        logger.error("Server did not become ready in time")

    def on_open(icon, item):
        webbrowser.open(DASHBOARD_URL)

    def on_quit(icon, item):
        logger.info("Quitting SAWALA")
        server_thread.stop()
        icon.stop()

    menu = Menu(
        MenuItem("Buka Dashboard", on_open, default=True),
        MenuItem("Keluar", on_quit),
    )

    icon_image = Image.open(_icon_path())
    tray_icon = Icon("Sawala", icon_image, "SAWALA", menu)
    tray_icon.run()


if __name__ == "__main__":
    main()
