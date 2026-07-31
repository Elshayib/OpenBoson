"""Tests for pre-migration database backups."""

from __future__ import annotations

from pathlib import Path

from openboson.db_backup import MAX_BACKUPS, backup_database, backups_dir


def test_backup_database_copies_and_prunes(isolated_home, tmp_path: Path):
    db = isolated_home / "openboson.db"
    db.write_bytes(b"sqlite-bytes")
    first = backup_database(db, reason="test")
    assert first is not None
    assert first.is_file()
    assert first.parent == backups_dir()

    for i in range(MAX_BACKUPS + 2):
        db.write_bytes(f"v{i}".encode())
        backup_database(db, reason="test")
    assert len(list(backups_dir().glob("openboson-*.db"))) <= MAX_BACKUPS


def test_backup_missing_db_returns_none(isolated_home):
    assert backup_database(isolated_home / "missing.db") is None
