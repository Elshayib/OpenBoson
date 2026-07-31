"""Persist custom exam presets as JSON under ``~/.openboson/custom_exams/``."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ConfigDict, Field

from openboson.config import settings
from openboson.exsim.custom_exam import CustomExamSpec

logger = logging.getLogger(__name__)


class CustomExamPreset(CustomExamSpec):
    """Saved custom exam specification with identity metadata."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = ""
    updated_at: str = ""


def presets_dir() -> Path:
    return settings.custom_exams_dir


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _preset_path(preset_id: str) -> Path:
    safe = "".join(c for c in preset_id if c.isalnum() or c in "-_")
    if not safe:
        raise ValueError("Invalid preset id")
    return presets_dir() / f"{safe}.json"


def list_presets() -> list[CustomExamPreset]:
    """Load all presets; skip corrupt files with a warning."""
    root = presets_dir()
    out: list[CustomExamPreset] = []
    for path in sorted(root.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                continue
            out.append(CustomExamPreset.model_validate(raw))
        except Exception as exc:
            logger.warning("Skipping corrupt custom exam preset %s: %s", path, exc)
    out.sort(key=lambda p: p.updated_at or p.created_at or p.id, reverse=True)
    return out


def get_preset(preset_id: str) -> CustomExamPreset | None:
    path = _preset_path(preset_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return CustomExamPreset.model_validate(raw)
    except Exception as exc:
        logger.warning("Failed to load custom exam preset %s: %s", path, exc)
        return None


def save_preset(spec: CustomExamSpec | CustomExamPreset | dict[str, Any]) -> CustomExamPreset:
    """Create or update a preset. Returns the persisted model."""
    if isinstance(spec, dict):
        data = dict(spec)
    elif isinstance(spec, CustomExamPreset):
        data = spec.model_dump()
    else:
        data = spec.model_dump()

    preset_id = str(data.get("id") or "").strip() or uuid.uuid4().hex[:12]
    existing = get_preset(preset_id)
    now = _now_iso()
    data["id"] = preset_id
    created = (existing.created_at if existing else None) or data.get("created_at") or now
    data["created_at"] = created
    data["updated_at"] = now
    preset = CustomExamPreset.model_validate(data)

    path = _preset_path(preset.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(preset.model_dump(), indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(prefix="custom-exam-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    return preset


def delete_preset(preset_id: str) -> bool:
    path = _preset_path(preset_id)
    if not path.is_file():
        return False
    path.unlink()
    return True
