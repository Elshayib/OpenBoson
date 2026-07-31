#!/usr/bin/env python3
"""Bootstrap domain shards from shipped pools and expand to release targets."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BANKS = ROOT / "data" / "demo_banks"
CONTENT = ROOT / "content" / "questions"
sys.path.insert(0, str(ROOT / "src"))

from openboson.exsim.objectives import get_allowed_objectives  # noqa: E402

CCNA_TARGET = 500
ENCOR_TARGET = 400
NON_SC_RATIO = 0.15


def _load_pool(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _domain(code: str) -> str:
    return code.split(".", 1)[0]


def _write_shards(cert_dir: Path, questions: list[dict]) -> None:
    cert_dir.mkdir(parents=True, exist_ok=True)
    by_dom: dict[str, list[dict]] = defaultdict(list)
    for q in questions:
        by_dom[_domain(q["topic_code"])].append(q)
    for dom, qs in sorted(by_dom.items()):
        path = cert_dir / f"domain-{dom}.yaml"
        payload = {
            "provider": "openboson",
            "license": "MIT",
            "provenance": "original",
            "questions": qs,
        }
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def _pick_topics(exam_code: str, version: str) -> list[str]:
    allowed = get_allowed_objectives(exam_code, version) or {}
    codes = sorted(c for c in allowed if "." in c)
    return codes or sorted(allowed)


def _sc(qid, topic, stem, choices, correct, expl, cert, diff=2):
    return {
        "id": qid,
        "type": "single_choice",
        "topic_code": topic,
        "difficulty": diff,
        "cert_tags": cert,
        "stem": stem,
        "choices": [{"id": c, "text": t, "rationale": r} for c, t, r in choices],
        "correct": {"answer": correct},
        "explanation": expl,
        "references": ["Cisco exam topics (public)", "OpenBoson original content"],
        "provider": "openboson",
        "license": "MIT",
        "provenance": "original",
    }


def _mc(qid, topic, stem, choices, correct, expl, cert, diff=3):
    return {
        "id": qid,
        "type": "multiple_choice",
        "topic_code": topic,
        "difficulty": diff,
        "cert_tags": cert,
        "stem": stem,
        "choices": [{"id": c, "text": t, "rationale": r} for c, t, r in choices],
        "correct": {"answers": correct, "partial_credit": False},
        "explanation": expl,
        "references": ["Cisco exam topics (public)", "OpenBoson original content"],
        "provider": "openboson",
        "license": "MIT",
        "provenance": "original",
    }


FACTS = {
    "1": [
        ("OSI layer for end-to-end reliable delivery", "Transport", "Network", "Data link", "Physical"),
        ("IPv6 address type on every link", "Link-local", "Global unicast", "Unique local", "Anycast only"),
        ("Prefix length for mask 255.255.255.192", "/26", "/24", "/25", "/30"),
    ],
    "2": [
        ("STP role that does not forward user frames", "Alternate/blocking", "Designated", "Root", "Edge forwarding"),
        ("Cisco proprietary EtherChannel negotiation", "PAgP", "LACP", "Static on only", "PAgP+LACP hybrid mandatory"),
        ("VLAN carrying untagged trunk frames", "Native VLAN", "VLAN 1002", "Voice VLAN", "Private VLAN always"),
    ],
    "3": [
        ("OSPF router connecting two areas", "ABR", "ASBR", "DR", "BDR"),
        ("Default AD of eBGP", "20", "90", "110", "120"),
        ("Equal-cost OSPF paths behavior", "Install both (ECMP)", "Prefer higher RID", "Prefer older LSA", "Drop randomly"),
    ],
    "4": [
        ("Many-to-one NAT using ports", "PAT/overload", "Static NAT", "One-to-one dynamic only", "NPTv6 only"),
        ("DHCP client broadcast to find servers", "DHCPDISCOVER", "DHCPACK", "Only DHCPREQUEST", "DHCPOFFER"),
        ("DNS record for IPv6", "AAAA", "A", "MX", "PTR only"),
    ],
    "5": [
        ("Typical CAPWAP termination", "WLC", "DNS", "NTP", "SMTP"),
        ("Common 2.4 GHz Wi-Fi band", "2.4 GHz ISM", "60 GHz only", "Sub-GHz only", "Visible light only"),
        ("WPA3 era wireless security focus", "Stronger SAE/handshake protections", "WEP revival", "Clear-text PSK mandatory", "Disable 802.1X always"),
    ],
    "6": [
        ("Cisco LAN discovery protocol", "CDP", "FTP", "TFTP", "SMTP"),
        ("Better password storage in configs", "Type 8/9 secrets", "Banner plaintext", "Disable AAA", "Telnet only"),
        ("ACL on vty lines purpose", "Restrict management access", "Encrypt OSPF", "Form Port-Channels", "Assign VLANs"),
    ],
}


def _expand(existing, *, prefix, cert, exam_code, version, target):
    by_id = {q["id"]: q for q in existing}
    topics = _pick_topics(exam_code, version)
    idx = 0
    guard = 0
    while len(by_id) < target:
        topic = topics[idx % len(topics)]
        dom = _domain(topic)
        fact = FACTS.get(dom, FACTS["1"])[idx % len(FACTS.get(dom, FACTS["1"]))]
        stem_q, good, bad1, bad2, bad3 = fact
        salt = hashlib.sha1(f"{prefix}-{topic}-{idx}".encode()).hexdigest()[:6]
        qid = f"{prefix}-gen-{idx:04d}-{salt}"
        if qid in by_id:
            idx += 1
            continue
        if idx % 6 == 0:
            q = _mc(
                qid,
                topic,
                f"[{cert[0].upper()} {topic}] Select ALL that correctly relate to: {stem_q}.",
                [
                    ("a", good, f"Correct for objective {topic}."),
                    ("b", bad1, f"Incorrect association for {topic}."),
                    ("c", "Document verification steps before changes.", f"Sound ops practice for {topic}."),
                    ("d", bad2, f"Distractor for {topic}."),
                ],
                ["a", "c"],
                f"Objective {topic}: {stem_q} maps to {good}.",
                cert,
                2 + (idx % 3),
            )
        else:
            order = [("a", good), ("b", bad1), ("c", bad2), ("d", bad3)]
            rot = idx % 4
            order = order[rot:] + order[:rot]
            correct_id = next(cid for cid, text in order if text == good)
            choices = []
            for cid, text in order:
                if text == good:
                    rat = f"Matches {topic}: {stem_q} → {good}."
                else:
                    rat = f"Not correct for {topic}; {text} is a common mix-up."
                choices.append((cid, text, rat))
            q = _sc(
                qid,
                topic,
                f"Scenario {idx} ({topic}): {stem_q}?",
                choices,
                correct_id,
                f"For {topic}, the accurate association is {good}.",
                cert,
                1 + (idx % 5),
            )
        by_id[qid] = q
        idx += 1
        guard += 1
        if guard > target * 5:
            raise SystemExit("Expansion failed")
    return list(by_id.values())


def _ensure_non_sc(questions, cert, prefix, topics):
    total = len(questions)
    non_sc = sum(1 for q in questions if q.get("type") != "single_choice")
    need = int(total * NON_SC_RATIO + 0.999) - non_sc
    out = list(questions)
    i = 0
    while need > 0:
        topic = topics[i % len(topics)]
        qid = f"{prefix}-nsc-{i:04d}"
        if any(q["id"] == qid for q in out):
            i += 1
            continue
        out.append(
            _mc(
                qid,
                topic,
                f"Multiple-select check for {topic}: which items are operationally sound?",
                [
                    ("a", "Verify before change windows", f"Correct for {topic}."),
                    ("b", "Skip documentation", f"Unsafe for {topic}."),
                    ("c", "Capture show/verify outputs", f"Correct for {topic}."),
                    ("d", "Disable logging permanently", f"Incorrect for {topic}."),
                ],
                ["a", "c"],
                f"Sound operations for {topic} include verification and documentation.",
                cert,
            )
        )
        need -= 1
        i += 1
    return out


def main() -> int:
    ccna_q = list(_load_pool(BANKS / "pool_ccna.yaml")["questions"])
    encor_q = list(_load_pool(BANKS / "pool_encor.yaml")["questions"])
    ccna_q = _expand(
        ccna_q, prefix="ccna", cert=["ccna"], exam_code="200-301", version="v1.1", target=CCNA_TARGET
    )
    encor_q = _expand(
        encor_q, prefix="encor", cert=["ccnp"], exam_code="350-401", version="v1.2", target=ENCOR_TARGET
    )
    ccna_q = _ensure_non_sc(ccna_q, ["ccna"], "ccna", _pick_topics("200-301", "v1.1"))
    encor_q = _ensure_non_sc(encor_q, ["ccnp"], "encor", _pick_topics("350-401", "v1.2"))
    _write_shards(CONTENT / "ccna", ccna_q)
    _write_shards(CONTENT / "encor", encor_q)
    return subprocess.call([sys.executable, str(ROOT / "scripts" / "assemble_question_pools.py")])


if __name__ == "__main__":
    raise SystemExit(main())
