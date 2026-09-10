"""Centralized application logging — console + rotating file at logs/app.log."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False

LOG_FORMAT = (
    "[%(asctime)s] [%(levelname)s] in %(module)s (%(filename)s:%(lineno)d): %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    *,
    level: int | None = None,
    log_dir: str | Path | None = None,
    force: bool = False,
) -> logging.Logger:
    """Configure root logger once: stdout + rotating logs/app.log (5MB × 3)."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return logging.getLogger("jakkas")

    if level is None:
        env_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        level = getattr(logging, env_level, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers on re-init (e.g. tests / create_app twice)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # File handler — skip on read-only serverless FS (Vercel)
    if not os.getenv("VERCEL"):
        base = Path(log_dir) if log_dir else Path(__file__).resolve().parent.parent / "logs"
        try:
            base.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                base / "app.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as exc:
            root.warning("Could not attach file log handler at %s: %s", base, exc)

    # Keep noisy libraries quieter unless debugging
    if level > logging.DEBUG:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    _CONFIGURED = True
    app_logger = logging.getLogger("jakkas")
    app_logger.debug("Logging configured (level=%s)", logging.getLevelName(level))
    return app_logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a named logger; ensures setup_logging has run."""
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name or "jakkas")
