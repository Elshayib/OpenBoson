"""Shared pytest fixtures for OpenBoson tests.

Redirects persistence away from the developer's real ``~/.openboson`` directory.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from openboson import stats_service
from openboson.db import init_db
from openboson.models import Base


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Point ``OPENBOSON_HOME`` and ``stats_service`` at a temporary database.

    Autouse is intentionally NOT enabled — tests that never touch persistence
    stay fast. Persistence and GUI flows that finish exams/labs should request
    this fixture (directly or via ``autouse`` in their module).
    """
    home = tmp_path / "openboson_home"
    home.mkdir()
    monkeypatch.setenv("OPENBOSON_HOME", str(home))

    db_path = home / "openboson.db"
    engine = init_db(create_engine(f"sqlite:///{db_path}", future=True))
    monkeypatch.setattr(stats_service, "_engine", engine)
    yield home
    monkeypatch.setattr(stats_service, "_engine", None)


@pytest.fixture
def temp_db_engine(tmp_path, monkeypatch):
    """Initialized engine bound into ``stats_service`` (no home redirect)."""
    db = tmp_path / "test.db"
    engine = init_db(create_engine(f"sqlite:///{db}", future=True))
    monkeypatch.setattr(stats_service, "_engine", engine)
    yield engine
    monkeypatch.setattr(stats_service, "_engine", None)


# Re-export Base for tests that still create schemas manually.
__all__ = ["Base", "isolated_home", "temp_db_engine"]
