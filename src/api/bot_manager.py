"""Runs bot/zoom_web_bot.py as a managed subprocess, so the host can start
and stop it straight from the dashboard instead of a server terminal.

Single-bot-at-a-time by design: the dashboard has one "join meeting" form,
and running two bots against the same session would just double-post
duplicate frames for the same participants."""
from __future__ import annotations

import subprocess
import sys
import threading
from collections import deque
from pathlib import Path

from src.utils.config import CONFIG, PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

_LOG_LINES_KEPT = 200


class BotManager:
    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._log: deque[str] = deque(maxlen=_LOG_LINES_KEPT)
        self._lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None

    def is_running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def status(self) -> dict:
        with self._lock:
            running = self._process is not None and self._process.poll() is None
            exit_code = None if running or self._process is None else self._process.returncode
            return {
                "running": running,
                "exit_code": exit_code,
                "log_tail": list(self._log),
            }

    def start(self, join_url: str, display_name: str, passcode: str | None, api_base: str) -> None:
        if self.is_running():
            raise RuntimeError("Bot sudah berjalan - hentikan dulu sebelum start baru")

        token = CONFIG.bot_ingest.get("token")
        if not token or token == "change-me":
            raise RuntimeError("bot_ingest.token belum diset di config.yaml (masih 'change-me')")

        python = sys.executable
        script = str(Path(PROJECT_ROOT) / "bot" / "zoom_web_bot.py")
        cmd = [
            python, script,
            "--join-url", join_url,
            "--display-name", display_name or "SAWALA",
            "--api-base", api_base,
            "--ingest-token", token,
        ]
        if passcode:
            cmd += ["--passcode", passcode]

        logger.info("Starting Zoom bot subprocess")
        self._log.clear()
        with self._lock:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(PROJECT_ROOT),
            )
            proc = self._process

        def _read_output():
            assert proc.stdout is not None
            for line in proc.stdout:
                self._log.append(line.rstrip("\n"))

        self._reader_thread = threading.Thread(target=_read_output, daemon=True)
        self._reader_thread.start()

    def stop(self) -> None:
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        logger.info("Stopping Zoom bot subprocess")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


bot_manager = BotManager()
