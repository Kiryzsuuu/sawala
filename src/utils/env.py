"""Loads secrets/environment-specific settings from .env (see .env.example).

Kept separate from config.yaml: config.yaml holds app *behavior* (thresholds,
capture settings) that's fine to commit; this module holds credentials that
must never be committed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.utils.config import PROJECT_ROOT


def _env_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / ".env"
    return PROJECT_ROOT / ".env"


load_dotenv(_env_path())


def _require_changed(name: str, value: str, placeholder: str) -> str:
    if value == placeholder:
        raise RuntimeError(
            f"{name} masih pakai nilai placeholder default. Isi .env dengan nilai "
            f"asli sebelum menjalankan server (lihat .env.example)."
        )
    return value


MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "sawala")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@sawala.local")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me-strong-password")

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-to-a-long-random-string")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "SAWALA")

PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:5173")

EMAIL_CONFIGURED = bool(SMTP_HOST and SMTP_USER and SMTP_APP_PASSWORD)


def assert_production_ready() -> None:
    """Called at startup only when SAWALA_ENV=production, so local dev with
    placeholder .env values still works without ceremony, but a real
    deployment refuses to boot with default secrets."""
    _require_changed("JWT_SECRET", JWT_SECRET, "change-me-to-a-long-random-string")
    _require_changed("ADMIN_PASSWORD", ADMIN_PASSWORD, "change-me-strong-password")
