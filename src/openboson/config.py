"""Application configuration and runtime paths.

All paths are computed lazily so that tests can override them via env vars or
monkeypatching ``Settings`` attributes.
"""

from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Runtime configuration. Override ``data_dir`` via ``OPENBOSON_HOME`` env."""

    app_name: str = "openboson"
    debug: bool = False

    @property
    def data_dir(self) -> Path:
        env = os.environ.get("OPENBOSON_HOME")
        path = Path(env) if env else Path.home() / f".{self.app_name}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "openboson.db"

    @property
    def banks_dir(self) -> Path:
        return self.data_dir / "banks"

    @property
    def labs_dir(self) -> Path:
        return self.data_dir / "labs"

    @property
    def packs_dir(self) -> Path:
        return self.data_dir / "packs"

    @property
    def custom_exams_dir(self) -> Path:
        path = self.data_dir / "custom_exams"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
