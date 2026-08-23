"""Load config.yaml into a nested, attribute-accessible object."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml


def _default_config_path() -> Path:
    """Under a PyInstaller build, config.yaml (and data/, logs/) must live
    next to the .exe, not inside the read-only bundled temp dir - so users
    can edit thresholds/region without rebuilding, and so the app doesn't
    lose written data when the temp extraction dir is cleaned up."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config.yaml"
    return Path(__file__).resolve().parents[2] / "config.yaml"


_CONFIG_PATH = _default_config_path()


class ConfigNode:
    """Wraps a dict so keys are accessible as attributes (read-only)."""

    def __init__(self, data: dict[str, Any]):
        for key, value in data.items():
            if isinstance(value, dict):
                value = ConfigNode(value)
            setattr(self, key, value)
        self._raw = data

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


def load_config(path: str | Path | None = None) -> ConfigNode:
    path = Path(path) if path else _CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ConfigNode(data)


CONFIG = load_config()

PROJECT_ROOT = _CONFIG_PATH.parent


def resolve_path(relative: str) -> Path:
    """Resolve a config path (e.g. './data/session.db') against project root."""
    p = Path(relative)
    if p.is_absolute():
        return p
    resolved = (PROJECT_ROOT / relative).resolve()
    os.makedirs(resolved.parent, exist_ok=True)
    return resolved
