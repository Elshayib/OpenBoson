"""Tests for the hot-load content registry."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from openboson.registry import (
    MAX_DEVICES_PER_LAB,
    MAX_QUESTIONS_PER_PACK,
    PROVENANCE_BUNDLED,
    PROVENANCE_LOCAL,
    get_registry,
    reset_registry,
)


@pytest.fixture(autouse=True)
def _isolated_registry(isolated_home):
    """Each test gets a fresh registry bound to an isolated OPENBOSON_HOME."""
    reset_registry()
    yield
    reset_registry()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _minimal_bank_yaml(*, code: str, question_ids: list[str]) -> str:
    questions = []
    for qid in question_ids:
        questions.append(
            {
                "id": qid,
                "type": "single_choice",
                "topic_code": "1.1",
                "difficulty": 1,
                "cert_tags": ["ccna"],
                "stem": f"Question {qid}?",
                "choices": [
                    {"id": "a", "text": "Yes", "rationale": "ok"},
                    {"id": "b", "text": "No", "rationale": "no"},
                ],
                "correct": {"answer": "a"},
                "explanation": "Because.",
            }
        )
    doc = {
        "title": f"Bank {code}",
        "code": code,
        "version": "v1",
        "provider": "test",
        "topics": [
            {"code": "1.0", "name": "Fundamentals", "weight": 0.2},
            {"code": "1.1", "name": "Components", "weight": 0.05},
        ],
        "questions": questions,
    }
    return yaml.safe_dump(doc, sort_keys=False)


def _minimal_lab_yaml(*, lab_id: str, n_devices: int = 1, n_tasks: int = 1) -> str:
    devices = [
        {
            "name": f"R{i + 1}",
            "type": "router",
            "interfaces": [{"name": "GigabitEthernet0/0"}],
        }
        for i in range(n_devices)
    ]
    tasks = [
        {
            "id": f"t{i + 1}",
            "instructions": f"Do task {i + 1}",
            "expected_config": f"hostname R{i + 1}",
            "grading_rules": {"require": [f"hostname R{i + 1}"]},
        }
        for i in range(n_tasks)
    ]
    doc = {
        "title": f"Lab {lab_id}",
        "lab_id": lab_id,
        "topic_code": "2.1",
        "difficulty": 2,
        "description": "Test lab",
        "topology": {"devices": devices, "links": []},
        "tasks": tasks,
    }
    return yaml.safe_dump(doc, sort_keys=False)


def _write_pack(
    packs_root: Path,
    pack_id: str,
    *,
    bank_yaml: str | None = None,
    lab_yaml: str | None = None,
    bank_name: str = "banks/extra.yaml",
    lab_name: str = "labs/extra.yaml",
    min_app_version: str = "0.1.0",
    extra_manifest: dict | None = None,
    tamper_hash: bool = False,
) -> Path:
    pack_dir = packs_root / pack_id
    pack_dir.mkdir(parents=True)
    files: list[dict[str, str]] = []

    if bank_yaml is not None:
        bank_path = pack_dir / bank_name
        bank_path.parent.mkdir(parents=True, exist_ok=True)
        bank_path.write_text(bank_yaml, encoding="utf-8")
        digest = "0" * 64 if tamper_hash else _sha256(bank_path)
        files.append({"path": bank_name.replace("\\", "/"), "sha256": digest})

    if lab_yaml is not None:
        lab_path = pack_dir / lab_name
        lab_path.parent.mkdir(parents=True, exist_ok=True)
        lab_path.write_text(lab_yaml, encoding="utf-8")
        files.append({"path": lab_name.replace("\\", "/"), "sha256": _sha256(lab_path)})

    manifest: dict = {
        "id": pack_id,
        "name": f"Pack {pack_id}",
        "version": "1.0.0",
        "schema_version": 1,
        "provider": "test",
        "license": "MIT",
        "cert_tags": ["ccna"],
        "min_app_version": min_app_version,
        "files": files,
    }
    if extra_manifest:
        manifest.update(extra_manifest)
    (pack_dir / "pack.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    return pack_dir


def test_bundled_content_loads():
    reg = get_registry()
    pool = reg.question_pool()
    labs = reg.labs()
    assert len(pool.questions) >= 200
    assert any(lab.lab_id == "ccna_branch_office_access" for lab in labs)
    diag = reg.diagnostics()
    assert diag.accepted_count >= 1
    assert any(a.provenance == PROVENANCE_BUNDLED for a in diag.accepted)


def test_get_registry_singleton():
    assert get_registry() is get_registry()


def test_local_bank_adds_new_questions(isolated_home):
    banks = isolated_home / "banks"
    banks.mkdir()
    (banks / "local.yaml").write_text(
        _minimal_bank_yaml(code="local-bank", question_ids=["local-q-1"]),
        encoding="utf-8",
    )
    reg = get_registry()
    pool = reg.question_pool()
    assert "local-q-1" in pool.by_id()
    assert any(a.provenance == PROVENANCE_LOCAL for a in reg.diagnostics().accepted)


def test_local_bank_collision_rejected(isolated_home):
    from openboson.bank_loader import load_question_pool
    from openboson.resource_paths import bundled_banks_dir

    colliding_id = load_question_pool(bundled_banks_dir()).questions[0].id

    banks = isolated_home / "banks"
    banks.mkdir()
    (banks / "collide.yaml").write_text(
        _minimal_bank_yaml(code="collide", question_ids=[colliding_id, "unique-ok"]),
        encoding="utf-8",
    )
    reg = get_registry()
    pool = reg.question_pool()
    assert colliding_id in pool.by_id()
    assert "unique-ok" not in pool.by_id()
    assert any("collision" in r.reason.lower() for r in reg.diagnostics().rejected)


def test_pack_adds_content(isolated_home):
    packs = isolated_home / "packs"
    _write_pack(
        packs,
        "demo-pack",
        bank_yaml=_minimal_bank_yaml(code="pack-bank", question_ids=["pack-q-1"]),
        lab_yaml=_minimal_lab_yaml(lab_id="pack-lab-1"),
    )
    reg = get_registry()
    assert "pack-q-1" in reg.question_pool().by_id()
    assert any(lab.lab_id == "pack-lab-1" for lab in reg.labs())
    assert any(a.provenance == "pack:demo-pack" for a in reg.diagnostics().accepted)


def test_pack_collision_rejects_whole_pack(isolated_home):
    from openboson.bank_loader import load_question_pool
    from openboson.resource_paths import bundled_banks_dir

    colliding_id = load_question_pool(bundled_banks_dir()).questions[0].id
    packs = isolated_home / "packs"
    _write_pack(
        packs,
        "bad-pack",
        bank_yaml=_minimal_bank_yaml(
            code="bad",
            question_ids=[colliding_id, "pack-only-q"],
        ),
        lab_yaml=_minimal_lab_yaml(lab_id="pack-only-lab"),
    )
    reg = get_registry()
    pool = reg.question_pool()
    assert "pack-only-q" not in pool.by_id()
    assert not any(lab.lab_id == "pack-only-lab" for lab in reg.labs())
    rejected = reg.diagnostics().rejected
    assert any("collision" in r.reason.lower() for r in rejected)
    assert any("bad-pack" in r.path or r.provenance == "pack:bad-pack" for r in rejected)


def test_pack_hash_mismatch_rejected(isolated_home):
    packs = isolated_home / "packs"
    _write_pack(
        packs,
        "tampered",
        bank_yaml=_minimal_bank_yaml(code="t", question_ids=["tamper-q"]),
        tamper_hash=True,
    )
    reg = get_registry()
    assert "tamper-q" not in reg.question_pool().by_id()
    assert any("sha-256" in r.reason.lower() for r in reg.diagnostics().rejected)


def test_pack_with_hooks_rejected(isolated_home):
    packs = isolated_home / "packs"
    _write_pack(
        packs,
        "hooked",
        bank_yaml=_minimal_bank_yaml(code="h", question_ids=["hook-q"]),
        extra_manifest={"hooks": {"post_install": "rm -rf /"}},
    )
    reg = get_registry()
    assert "hook-q" not in reg.question_pool().by_id()
    assert any("hook" in r.reason.lower() for r in reg.diagnostics().rejected)


def test_pack_external_path_rejected(isolated_home):
    packs = isolated_home / "packs"
    pack_dir = packs / "ext"
    pack_dir.mkdir(parents=True)
    bank_path = pack_dir / "ok.yaml"
    bank_path.write_text(
        _minimal_bank_yaml(code="e", question_ids=["ext-q"]),
        encoding="utf-8",
    )
    manifest = {
        "id": "ext",
        "name": "External",
        "version": "1.0.0",
        "schema_version": 1,
        "provider": "test",
        "license": "MIT",
        "cert_tags": ["ccna"],
        "min_app_version": "0.1.0",
        "files": [
            {"path": "../banks/escape.yaml", "sha256": _sha256(bank_path)},
        ],
    }
    (pack_dir / "pack.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    reg = get_registry()
    assert any(
        "parent" in r.reason.lower() or "not allowed" in r.reason.lower()
        for r in reg.diagnostics().rejected
    )


def test_file_size_limit(isolated_home, monkeypatch):
    monkeypatch.setattr("openboson.registry.MAX_FILE_BYTES", 200)
    banks = isolated_home / "banks"
    banks.mkdir()
    big = "x" * 500
    content = _minimal_bank_yaml(code="big", question_ids=["big-q"]) + f"\n# {big}\n"
    (banks / "big.yaml").write_text(content, encoding="utf-8")
    assert (banks / "big.yaml").stat().st_size > 200
    reg = get_registry()
    assert "big-q" not in reg.question_pool().by_id()
    assert any("size limit" in r.reason.lower() for r in reg.diagnostics().rejected)


def test_lab_device_limit(isolated_home):
    labs = isolated_home / "labs"
    labs.mkdir()
    (labs / "too_many.yaml").write_text(
        _minimal_lab_yaml(
            lab_id="too-many-devices",
            n_devices=MAX_DEVICES_PER_LAB + 1,
        ),
        encoding="utf-8",
    )
    reg = get_registry()
    assert not any(lab.lab_id == "too-many-devices" for lab in reg.labs())
    assert any(
        "device" in r.reason.lower()
        and ("limit" in r.reason.lower() or "maximum" in r.reason.lower())
        for r in reg.diagnostics().rejected
    )


def test_pack_question_limit(isolated_home, monkeypatch):
    monkeypatch.setattr("openboson.registry.MAX_QUESTIONS_PER_PACK", 2)
    packs = isolated_home / "packs"
    _write_pack(
        packs,
        "overflow",
        bank_yaml=_minimal_bank_yaml(
            code="ov",
            question_ids=["oq1", "oq2", "oq3"],
        ),
    )
    reg = get_registry()
    assert "oq1" not in reg.question_pool().by_id()
    assert any("question limit" in r.reason.lower() for r in reg.diagnostics().rejected)
    assert MAX_QUESTIONS_PER_PACK >= 2


def test_refresh_invalidates_cache(isolated_home):
    reg = get_registry()
    before = len(reg.question_pool().questions)

    banks = isolated_home / "banks"
    banks.mkdir()
    (banks / "new.yaml").write_text(
        _minimal_bank_yaml(code="after", question_ids=["after-refresh-q"]),
        encoding="utf-8",
    )

    diag = reg.refresh()
    assert "after-refresh-q" in reg.question_pool().by_id()
    assert len(reg.question_pool().questions) == before + 1
    assert diag.accepted_count >= 1

    (banks / "new.yaml").unlink()
    reg.refresh()
    assert "after-refresh-q" not in reg.question_pool().by_id()


def test_cache_reuses_until_mtime_changes(isolated_home):
    reg = get_registry()
    first = reg.question_pool()
    second = reg.question_pool()
    assert first is second

    banks = isolated_home / "banks"
    banks.mkdir(exist_ok=True)
    (banks / "cached.yaml").write_text(
        _minimal_bank_yaml(code="cached", question_ids=["cached-q"]),
        encoding="utf-8",
    )
    third = reg.question_pool()
    assert "cached-q" in third.by_id()
    assert third is not first


def test_invalid_pack_missing_manifest(isolated_home):
    packs = isolated_home / "packs"
    (packs / "empty-pack").mkdir(parents=True)
    reg = get_registry()
    assert any("missing pack.yaml" in r.reason.lower() for r in reg.diagnostics().rejected)


def test_min_app_version_too_high(isolated_home):
    packs = isolated_home / "packs"
    _write_pack(
        packs,
        "future",
        bank_yaml=_minimal_bank_yaml(code="f", question_ids=["future-q"]),
        min_app_version="99.0.0",
    )
    reg = get_registry()
    assert "future-q" not in reg.question_pool().by_id()
    assert any("requires app version" in r.reason.lower() for r in reg.diagnostics().rejected)


def test_content_api_refresh_and_diagnostics(isolated_home):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from openboson.exsim import router as exsim_router
    from openboson.netsim import router as netsim_router
    from openboson.server import app

    exsim_router.clear_content_cache()
    netsim_router.clear_content_cache()

    client = TestClient(app)
    diag = client.get("/api/v1/content/diagnostics")
    assert diag.status_code == 200
    body = diag.json()
    assert "accepted_count" in body
    assert "rejected_count" in body

    banks = isolated_home / "banks"
    banks.mkdir(exist_ok=True)
    (banks / "api.yaml").write_text(
        _minimal_bank_yaml(code="api", question_ids=["api-refresh-q"]),
        encoding="utf-8",
    )
    refreshed = client.post("/api/v1/content/refresh")
    assert refreshed.status_code == 200
    assert "api-refresh-q" in get_registry().question_pool().by_id()
