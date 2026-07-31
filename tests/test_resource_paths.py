"""Tests for bundled resource path resolution."""

from __future__ import annotations

from pathlib import Path

import openboson.resource_paths as rp


def test_source_layout_finds_bundled_banks_and_labs():
    banks = rp.bundled_banks_dir()
    labs = rp.bundled_labs_dir()
    assert banks.is_dir()
    assert labs.is_dir()
    assert any(banks.glob("*.yaml"))
    assert any(labs.glob("*.yaml"))
    assert rp.gui_styles_path().is_file()
    assert not rp.is_frozen()
    assert rp.repo_root() is not None


def test_frozen_layout_uses_meipass(monkeypatch, tmp_path: Path):
    data = tmp_path / "data"
    (data / "demo_banks").mkdir(parents=True)
    (data / "demo_labs").mkdir(parents=True)
    (data / "demo_banks" / "pool.yaml").write_text("x: 1\n", encoding="utf-8")
    monkeypatch.setattr(rp.sys, "frozen", True, raising=False)
    monkeypatch.setattr(rp.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert rp.is_frozen()
    assert rp.bundled_data_dir() == data
    assert rp.bundled_banks_dir() == data / "demo_banks"
