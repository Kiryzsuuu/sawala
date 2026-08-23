"""Centralized logger setup."""
import logging
import sys

from src.utils.config import CONFIG, resolve_path


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, str(CONFIG.logging.get("level", "INFO")).upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # sys.stdout is None under a windowed (no-console) PyInstaller build -
    # only attach the console handler when there's an actual stream to write to.
    if sys.stdout is not None:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(fmt)
        logger.addHandler(stream_handler)

    log_file = CONFIG.logging.get("file")
    if log_file:
        file_path = resolve_path(log_file)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger
