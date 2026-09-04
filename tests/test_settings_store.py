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
    assert cfg.theme == "light"
    assert cfg.check_updates_on_startup is True
    assert cfg.update_channel == "stable"
    assert cfg.onboarding_complete is False
    assert cfg.preferred_cert is None


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
    assert load_settings().theme == "light"


def test_onboarding_fields_round_trip(isolated_home):
    saved = save_settings(AppSettings(onboarding_complete=True, preferred_cert="ccna"))
    assert saved.onboarding_complete is True
    assert saved.preferred_cert == "ccna"
    loaded = load_settings()
    assert loaded.onboarding_complete is True
    assert loaded.preferred_cert == "ccna"


def test_preferred_cert_invalid_coerces_to_none(isolated_home):
    save_settings({"onboarding_complete": True, "preferred_cert": "encor"})
    loaded = load_settings()
    assert loaded.onboarding_complete is True
    assert loaded.preferred_cert is None
