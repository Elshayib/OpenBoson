"""Typed user settings with atomic JSON persistence."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Literal

from openboson.config import settings

logger = logging.getLogger(__name__)

SETTINGS_SCHEMA_VERSION = 1
UpdateChannel = Literal["stable", "beta"]
ThemeName = Literal["dark", "light"]


@dataclass
class AppSettings:
    """Persisted application preferences."""

    theme: ThemeName = "dark"
    check_updates_on_startup: bool = True
    update_channel: UpdateChannel = "stable"
    last_update_check: str | None = None
    skipped_version: str | None = None
    schema_version: int = SETTINGS_SCHEMA_VERSION


def settings_path() -> Path:
    return settings.data_dir / "settings.json"


def default_settings() -> AppSettings:
    return AppSettings()


def _coerce(raw: dict[str, Any]) -> AppSettings:
    base = asdict(default_settings())
    base.update({k: v for k, v in raw.items() if k in base})
    theme = base.get("theme", "dark")
    if theme not in ("dark", "light"):
        theme = "dark"
    channel = base.get("update_channel", "stable")
    if channel not in ("stable", "beta"):
        channel = "stable"
    return AppSettings(
        theme=theme,  # type: ignore[arg-type]
        check_updates_on_startup=bool(base.get("check_updates_on_startup", True)),
        update_channel=channel,  # type: ignore[arg-type]
        last_update_check=base.get("last_update_check"),
        skipped_version=base.get("skipped_version"),
        schema_version=int(base.get("schema_version") or SETTINGS_SCHEMA_VERSION),
    )


def load_settings() -> AppSettings:
    """Load settings from disk, merging with defaults on missing/corrupt files."""
    path = settings_path()
    if not path.is_file():
        return default_settings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_settings()
        return _coerce(raw)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("Failed to load settings from %s: %s", path, exc)
        return default_settings()


def save_settings(data: AppSettings | dict[str, Any]) -> AppSettings:
    """Persist settings atomically (temp file + replace)."""
    if isinstance(data, dict):
        current = asdict(load_settings())
        current.update(data)
        app = _coerce(current)
    else:
        app = data
    app.schema_version = SETTINGS_SCHEMA_VERSION
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(app), indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(prefix="settings-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return app


def update_settings(**kwargs: Any) -> AppSettings:
    """Patch selected fields and save."""
    current = asdict(load_settings())
    allowed = {f.name for f in fields(AppSettings)}
    for key, value in kwargs.items():
        if key not in allowed:
            raise KeyError(f"Unknown settings key: {key}")
        current[key] = value
    return save_settings(current)
