"""Versioned Cisco exam objective registries for question tagging.

Source: Cisco official exam topics PDFs / Learning Network listings.
Refresh date: 2026-07-31.
"""

from __future__ import annotations

from collections.abc import Iterable

# CCNA 200-301 v1.1 — leaf objectives (two-level codes used by OpenBoson banks).
CCNA_200_301_V1_1: frozenset[str] = frozenset(
    {
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "1.5",
        "1.6",
        "1.7",
        "1.8",
        "1.9",
        "1.10",
        "1.11",
        "1.12",
        "1.13",
        "2.1",
        "2.2",
        "2.3",
        "2.4",
        "2.5",
        "2.6",
        "2.7",
        "2.8",
        "2.9",
        "3.1",
        "3.2",
        "3.3",
        "3.4",
        "3.5",
        "4.1",
        "4.2",
        "4.3",
        "4.4",
        "4.5",
        "4.6",
        "4.7",
        "4.8",
        "4.9",
        "5.1",
        "5.2",
        "5.3",
        "5.4",
        "5.5",
        "5.6",
        "5.7",
        "5.8",
        "5.9",
        "5.10",
        "6.1",
        "6.2",
        "6.3",
        "6.4",
        "6.5",
        "6.6",
        "6.7",
    }
)

# ENCOR 350-401 v1.2 — leaf objectives (wireless infrastructure removed vs v1.1).
ENCOR_350_401_V1_2: frozenset[str] = frozenset(
    {
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "2.1",
        "2.2",
        "2.3",
        "3.1",
        "3.2",
        "3.3",
        "4.1",
        "4.2",
        "4.3",
        "4.4",
        "4.5",
        "4.6",
        "5.1",
        "5.2",
        "5.3",
        "5.4",
        "6.1",
        "6.2",
        "6.3",
        "6.4",
        "6.5",
        "6.6",
        "6.7",
    }
)

_OBJECTIVES_BY_KEY: dict[tuple[str, str], frozenset[str]] = {
    ("200-301", "v1.1"): CCNA_200_301_V1_1,
    ("350-401", "v1.2"): ENCOR_350_401_V1_2,
}

# Demo pool codes map to official exam identity for validation.
_POOL_CODE_ALIASES: dict[str, tuple[str, str]] = {
    "pool-ccna": ("200-301", "v1.1"),
    "pool-encor": ("350-401", "v1.2"),
    "200-301": ("200-301", "v1.1"),
    "350-401": ("350-401", "v1.2"),
}


def normalize_exam_version(version: str) -> str:
    """Normalize version strings like ``1.1`` / ``V1.2`` to ``v1.1`` form."""
    v = version.strip().lower()
    if not v.startswith("v"):
        v = f"v{v}"
    return v


def get_allowed_objectives(exam_code: str, version: str) -> frozenset[str] | None:
    """Return the allowed leaf objective set, or ``None`` if unknown."""
    key = (exam_code.strip(), normalize_exam_version(version))
    if key in _OBJECTIVES_BY_KEY:
        return _OBJECTIVES_BY_KEY[key]
    alias = _POOL_CODE_ALIASES.get(exam_code.strip())
    if alias is not None:
        # Prefer explicit version when provided; alias version is fallback identity.
        aliased = (alias[0], normalize_exam_version(version) if version else alias[1])
        if aliased in _OBJECTIVES_BY_KEY:
            return _OBJECTIVES_BY_KEY[aliased]
        return _OBJECTIVES_BY_KEY.get(alias)
    return None


def resolve_objective_key(exam_code: str, version: str) -> tuple[str, str] | None:
    """Resolve ``(official_code, version)`` for a bank/pool code, if known."""
    code = exam_code.strip()
    ver = normalize_exam_version(version)
    if (code, ver) in _OBJECTIVES_BY_KEY:
        return code, ver
    alias = _POOL_CODE_ALIASES.get(code)
    if alias is None:
        return None
    # When the bank version matches a known map for the aliased exam, use it.
    if (alias[0], ver) in _OBJECTIVES_BY_KEY:
        return alias[0], ver
    return alias


def objective_allowed(topic_code: str, allowed: frozenset[str]) -> bool:
    """True if ``topic_code`` is an exact allowed leaf or a child of one."""
    if topic_code in allowed:
        return True
    parts = topic_code.split(".")
    for i in range(len(parts) - 1, 0, -1):
        parent = ".".join(parts[:i])
        if parent in allowed:
            return True
    return False


def invalid_topic_codes(
    topic_codes: Iterable[str],
    exam_code: str,
    version: str,
) -> list[str]:
    """Return topic codes not covered by the versioned objective map."""
    allowed = get_allowed_objectives(exam_code, version)
    if allowed is None:
        raise KeyError(f"No objective registry for {exam_code} {version}")
    return [code for code in topic_codes if not objective_allowed(code, allowed)]
