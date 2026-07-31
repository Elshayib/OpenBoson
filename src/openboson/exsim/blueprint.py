"""Exam blueprint presets and weighted question sampling.

Blueprints describe real-exam-like CCNA / CCNP runs: fixed length, time,
pass score, and domain weights. Questions are drawn from the shared pool
without replacement.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from openboson.bank_schema import CertTag, ExamBank, Question, Topic


@dataclass(frozen=True)
class DomainWeight:
    """Weight for a domain prefix such as ``\"1.\"`` or ``\"1\"``."""

    prefix: str  # normalized without trailing dot for matching, e.g. "1"
    weight: float
    name: str = ""


@dataclass(frozen=True)
class ExamBlueprint:
    """A one-click exam preset."""

    id: str
    title: str
    code: str
    cert: CertTag
    question_count: int
    time_limit_minutes: int
    pass_score: float
    domain_weights: tuple[DomainWeight, ...]
    enabled: bool = True
    coming_soon_label: str | None = None


class InsufficientPoolError(Exception):
    """Raised when the pool cannot fill a blueprint without replacement."""

    def __init__(self, message: str, deficits: dict[str, int] | None = None) -> None:
        super().__init__(message)
        self.deficits = deficits or {}


# Official-ish CCNA 200-301 v1.1 domain weights (Cisco published %).
_CCNA_DOMAINS: tuple[DomainWeight, ...] = (
    DomainWeight("1", 0.20, "Network Fundamentals"),
    DomainWeight("2", 0.20, "Network Access"),
    DomainWeight("3", 0.25, "IP Connectivity"),
    DomainWeight("4", 0.10, "IP Services"),
    DomainWeight("5", 0.15, "Security Fundamentals"),
    DomainWeight("6", 0.10, "Automation and Programmability"),
)

# ENCOR 350-401 domain weights (Cisco published %).
_ENCOR_DOMAINS: tuple[DomainWeight, ...] = (
    DomainWeight("1", 0.15, "Architecture"),
    DomainWeight("2", 0.20, "Virtualization"),
    DomainWeight("3", 0.20, "Infrastructure"),
    DomainWeight("4", 0.15, "Network Assurance"),
    DomainWeight("5", 0.20, "Security"),
    DomainWeight("6", 0.10, "Automation"),
)

BLUEPRINTS: dict[str, ExamBlueprint] = {
    "ccna-200-301": ExamBlueprint(
        id="ccna-200-301",
        title="CCNA 200-301 Practice Exam",
        code="200-301",
        cert="ccna",
        question_count=100,
        time_limit_minutes=120,
        pass_score=0.825,
        domain_weights=_CCNA_DOMAINS,
        enabled=True,
    ),
    "encor-350-401": ExamBlueprint(
        id="encor-350-401",
        title="CCNP ENCOR 350-401 Practice Exam",
        code="350-401",
        cert="ccnp",
        question_count=100,
        time_limit_minutes=120,
        pass_score=0.825,
        domain_weights=_ENCOR_DOMAINS,
        enabled=True,
    ),
    "enarsi-300-410": ExamBlueprint(
        id="enarsi-300-410",
        title="CCNP ENARSI 300-410 Practice Exam",
        code="300-410",
        cert="ccnp",
        question_count=100,
        time_limit_minutes=120,
        pass_score=0.825,
        domain_weights=_ENCOR_DOMAINS,  # placeholder weights
        enabled=False,
        coming_soon_label="Coming soon",
    ),
}


def list_blueprints() -> list[ExamBlueprint]:
    return list(BLUEPRINTS.values())


def get_blueprint(blueprint_id: str) -> ExamBlueprint:
    try:
        return BLUEPRINTS[blueprint_id]
    except KeyError as exc:
        raise KeyError(f"Unknown blueprint: {blueprint_id}") from exc


def _domain_prefix(topic_code: str) -> str:
    return topic_code.split(".", 1)[0]


def allocate_counts(total: int, weights: tuple[DomainWeight, ...]) -> dict[str, int]:
    """Largest-remainder method so allocated counts sum exactly to ``total``."""
    if total < 0:
        raise ValueError("total must be non-negative")
    weight_sum = sum(d.weight for d in weights)
    if weight_sum <= 0:
        raise ValueError("domain weights must sum to a positive value")

    raw = [(d.prefix, total * (d.weight / weight_sum)) for d in weights]
    floors = {p: int(v) for p, v in raw}
    remainders = sorted(((v - floors[p], p) for p, v in raw), reverse=True)
    assigned = sum(floors.values())
    leftover = total - assigned
    for i in range(leftover):
        floors[remainders[i % len(remainders)][1]] += 1
    return floors


def build_exam_from_blueprint(
    pool_questions: list[Question],
    blueprint: ExamBlueprint,
    *,
    rng: random.Random | None = None,
) -> list[Question]:
    """Sample questions for ``blueprint`` without replacement.

    Raises :class:`InsufficientPoolError` if any domain lacks enough questions.
    """
    if not blueprint.enabled:
        raise InsufficientPoolError(f"Blueprint {blueprint.id} is not enabled")

    rng = rng or random.Random()
    eligible = [q for q in pool_questions if q.matches_cert(blueprint.cert)]
    by_domain: dict[str, list[Question]] = {}
    for q in eligible:
        by_domain.setdefault(_domain_prefix(q.topic_code), []).append(q)

    counts = allocate_counts(blueprint.question_count, blueprint.domain_weights)
    deficits: dict[str, int] = {}
    selected: list[Question] = []

    for domain in blueprint.domain_weights:
        need = counts.get(domain.prefix, 0)
        available = list(by_domain.get(domain.prefix, []))
        if len(available) < need:
            deficits[domain.prefix] = need - len(available)
            continue
        rng.shuffle(available)
        selected.extend(available[:need])

    if deficits:
        parts = [
            f"domain {p} needs {n} more question(s)" for p, n in sorted(deficits.items())
        ]
        raise InsufficientPoolError(
            f"Not enough questions for {blueprint.title}: " + "; ".join(parts),
            deficits=deficits,
        )

    rng.shuffle(selected)
    return selected


def bank_from_blueprint(
    blueprint: ExamBlueprint,
    questions: list[Question],
) -> ExamBank:
    """Wrap sampled questions in an ``ExamBank`` for session/scoring."""
    topics = [
        Topic(code=f"{d.prefix}.0", name=d.name or f"Domain {d.prefix}", weight=d.weight)
        for d in blueprint.domain_weights
    ]
    return ExamBank(
        title=blueprint.title,
        code=blueprint.code,
        version="v1.1",
        provider="openboson",
        description=f"Blueprint exam ({blueprint.id})",
        topics=topics,
        pass_score=blueprint.pass_score,
        time_limit_minutes=blueprint.time_limit_minutes,
        questions=questions,
    )


@dataclass
class PoolCoverage:
    """How many cert-tagged questions exist per domain for a blueprint."""

    blueprint_id: str
    counts: dict[str, int] = field(default_factory=dict)
    required: dict[str, int] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return all(self.counts.get(p, 0) >= need for p, need in self.required.items())

    @property
    def deficits(self) -> dict[str, int]:
        return {
            p: need - self.counts.get(p, 0)
            for p, need in self.required.items()
            if self.counts.get(p, 0) < need
        }


def coverage_for_blueprint(
    pool_questions: list[Question], blueprint: ExamBlueprint
) -> PoolCoverage:
    eligible = [q for q in pool_questions if q.matches_cert(blueprint.cert)]
    counts: dict[str, int] = {d.prefix: 0 for d in blueprint.domain_weights}
    for q in eligible:
        p = _domain_prefix(q.topic_code)
        if p in counts:
            counts[p] += 1
    required = allocate_counts(blueprint.question_count, blueprint.domain_weights)
    return PoolCoverage(blueprint_id=blueprint.id, counts=counts, required=required)
