"""Application logging setup (rotating file under the user data directory)."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from openboson.config import settings

_CONFIGURED = False
LOG_NAME = "openboson.log"
MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5


def logs_dir() -> Path:
    path = settings.data_dir / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_file_path() -> Path:
    return logs_dir() / LOG_NAME


def setup_logging(*, level: int = logging.INFO, force: bool = False) -> Path:
    """Configure root/app logging once. Returns the log file path."""
    global _CONFIGURED
    path = log_file_path()
    if _CONFIGURED and not force:
        return path

    root = logging.getLogger()
    root.setLevel(level)

    # Remove previous OpenBoson file handlers when reconfiguring (tests).
    for handler in list(root.handlers):
        if getattr(handler, "_openboson_handler", False):
            root.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.handlers.RotatingFileHandler(
        path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    file_handler._openboson_handler = True  # type: ignore[attr-defined]
    root.addHandler(file_handler)

    if not any(
        isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.handlers.RotatingFileHandler)
        for h in root.handlers
    ):
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        stream.setLevel(level)
        stream._openboson_handler = True  # type: ignore[attr-defined]
        root.addHandler(stream)

    _CONFIGURED = True
    logging.getLogger("openboson").debug("Logging configured at %s", path)
    return path
