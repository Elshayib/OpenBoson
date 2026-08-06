"""Filter helpers for the NetSim lab catalog."""

from __future__ import annotations

from openboson.netsim.lab_schema import LabBank


def filter_labs(
    labs: list[LabBank],
    *,
    topic_code: str | None = None,
    difficulty: int | None = None,
    cert: str | None = None,
    q: str | None = None,
    lab_tier: str | None = None,
) -> list[LabBank]:
    """Return labs matching catalog filters (all filters ANDed).

    - ``topic_code``: exact match, or domain prefix (``2`` / ``2.``) against ``lab.topic_code``
    - ``difficulty``: exact 1–5
    - ``cert``: must appear in ``lab.cert_tags``
    - ``q``: case-insensitive substring against title, description, objectives, topic_code
    - ``lab_tier``: ``gold`` / ``drill`` / ``scale`` (or display labels)
    """
    topic = (topic_code or "").strip()
    needle = (q or "").strip().lower()
    cert_n = (cert or "").strip().lower() or None
    tier_n = (lab_tier or "").strip().lower() or None
    tier_aliases = {
        "scenario": "gold",
        "gold": "gold",
        "cli drill": "drill",
        "drill": "drill",
        "scale": "scale",
    }
    if tier_n:
        tier_n = tier_aliases.get(tier_n, tier_n)
    out: list[LabBank] = []
    for lab in labs:
        if topic and topic.lower() not in ("all", "*"):
            code = (lab.topic_code or "").strip()
            prefix = topic.rstrip(".")
            if code not in (topic, prefix) and not code.startswith(prefix + "."):
                continue
        if difficulty is not None and int(lab.difficulty) != int(difficulty):
            continue
        if cert_n and cert_n not in ("all", "*"):
            tags = [t.lower() for t in (lab.cert_tags or [])]
            if cert_n not in tags:
                continue
        if tier_n and tier_n not in ("all", "*") and lab.lab_tier.value != tier_n:
            continue
        if needle:
            blob = " ".join(
                [
                    lab.title or "",
                    lab.description or "",
                    lab.topic_code or "",
                    " ".join(lab.objectives or []),
                    lab.lab_tier.value,
                ]
            ).lower()
            if needle not in blob:
                continue
        out.append(lab)
    return out


def tier_badge(lab: LabBank) -> str:
    """Short catalog badge for Scenario / CLI drill / Scale."""
    if lab.lab_tier.value == "gold":
        return "Scenario"
    if lab.lab_tier.value == "scale":
        return "Scale"
    return "CLI drill"
