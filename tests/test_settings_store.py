"""Tests for typed settings persistence."""

from __future__ import annotations

from openboson.settings_store import (
    AppSettings,
    load_settings,
    save_settings,
    settings_path,
    update_settings,
)


def test_defaults_when_missing(isolated_home):
    assert not settings_path().exists()
    cfg = load_settings()
    assert cfg.theme == "dark"
    assert cfg.check_updates_on_startup is True
    assert cfg.update_channel == "stable"


def test_round_trip_atomic(isolated_home):
    saved = save_settings(AppSettings(theme="light", update_channel="beta"))
    assert saved.theme == "light"
    assert settings_path().is_file()
    loaded = load_settings()
    assert loaded.theme == "light"
    assert loaded.update_channel == "beta"


def test_update_settings_patch(isolated_home):
    update_settings(skipped_version="0.2.0")
    assert load_settings().skipped_version == "0.2.0"
    assert load_settings().theme == "dark"
