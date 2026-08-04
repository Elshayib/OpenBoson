#!/usr/bin/env python3
"""Assemble domain-sharded question sources into shipped demo bank pools."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "content" / "questions"
OUT = ROOT / "data" / "demo_banks"
sys.path.insert(0, str(ROOT / "src"))

from openboson.exsim.objectives import (  # noqa: E402
    get_allowed_objectives,
    invalid_topic_codes,
    topic_title,
)


def _load_shard(path: Path) -> list[dict]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, dict) and isinstance(raw.get("questions"), list):
        return list(raw["questions"])
    raise SystemExit(f"Unexpected shard format: {path}")


def _collect(cert_folder: str) -> list[dict]:
    root = SRC / cert_folder
    if not root.is_dir():
        raise SystemExit(f"Missing content directory: {root}")
    questions: list[dict] = []
    for path in sorted(root.glob("domain-*.yaml")):
        questions.extend(_load_shard(path))
    return questions


def _topics_for(questions: list[dict], exam_code: str, version: str) -> list[dict]:
    allowed = set(get_allowed_objectives(exam_code, version) or [])
    used = sorted({q["topic_code"] for q in questions})
    # Keep declared topics even if the objective map is temporarily incomplete.
    out: list[dict] = []
    for code in used:
        if allowed and code not in allowed:
            continue
        title = topic_title(code, cert=exam_code) or code
        out.append({"code": code, "name": title})
    return out


def main() -> int:
    ccna_q = _collect("ccna")
    encor_q = _collect("encor")

    for label, qs, exam, ver in (
        ("ccna", ccna_q, "200-301", "v1.1"),
        ("encor", encor_q, "350-401", "v1.2"),
    ):
        ids = [q["id"] for q in qs]
        if len(ids) != len(set(ids)):
            dup = [i for i, c in Counter(ids).items() if c > 1]
            raise SystemExit(f"Duplicate ids in {label}: {dup[:10]}")
        bad = invalid_topic_codes((q["topic_code"] for q in qs), exam, ver)
        if bad:
            raise SystemExit(f"Invalid topics in {label}: {sorted(set(bad))[:20]}")

    OUT.mkdir(parents=True, exist_ok=True)
    ccna_bank = {
        "title": "OpenBoson CCNA Pool",
        "code": "pool-ccna",
        "version": "v1.1",
        "provider": "openboson",
        "description": "OpenBoson CCNA question pool (assembled from domain shards)",
        "cert_tags": ["ccna"],
        "topics": _topics_for(ccna_q, "200-301", "v1.1"),
        "questions": ccna_q,
    }
    encor_bank = {
        "title": "OpenBoson ENCOR Pool",
        "code": "pool-encor",
        "version": "v1.2",
        "provider": "openboson",
        "description": "OpenBoson ENCOR question pool (assembled from domain shards)",
        "cert_tags": ["ccnp"],
        "topics": _topics_for(encor_q, "350-401", "v1.2"),
        "questions": encor_q,
    }
    (OUT / "pool_ccna.yaml").write_text(
        yaml.safe_dump(ccna_bank, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (OUT / "pool_encor.yaml").write_text(
        yaml.safe_dump(encor_bank, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Wrote {len(ccna_q)} CCNA and {len(encor_q)} ENCOR questions to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
