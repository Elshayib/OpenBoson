"""Database backup helpers used before schema migrations."""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

from openboson import __version__
from openboson.config import settings

logger = logging.getLogger(__name__)

MAX_BACKUPS = 5


def backups_dir() -> Path:
    path = settings.data_dir / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def backup_database(db_path: Path | None = None, *, reason: str = "migration") -> Path | None:
    """Copy the SQLite DB into backups/, retaining the newest ``MAX_BACKUPS`` files.

    Returns the backup path, or ``None`` when there is nothing to back up.
    """
    path = Path(db_path) if db_path is not None else settings.db_path
    if not path.is_file():
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_version = __version__.replace("/", "-")
    dest = backups_dir() / f"openboson-{safe_version}-{stamp}.db"
    shutil.copy2(path, dest)
    logger.info("Database backup created (%s): %s", reason, dest)
    _prune_backups()
    return dest


def _prune_backups() -> None:
    files = sorted(
        backups_dir().glob("openboson-*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for stale in files[MAX_BACKUPS:]:
        try:
            stale.unlink()
            logger.debug("Pruned old backup %s", stale)
        except OSError as exc:
            logger.warning("Failed to prune backup %s: %s", stale, exc)
