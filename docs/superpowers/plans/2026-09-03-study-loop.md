# Study Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. **Depends on:** gold labs having honest topic_codes (track 4 helps; can start after NAT if matching existing labs).

**Boson gate:** Boson sells ExSim and NetSim separately. This loop is the
combined-product win. A candidate with a weak domain 2.x can start a matching
gold lab in one click. File ownership: `stats_service.py`, `gui/engine.py`,
Dashboard, Stats, `main_window.py` navigation — not QSS, not practice Check.

**Goal:** After a weak domain is known, Stats and Home offer one click to practice that domain **or** start a gold lab whose `topic_code` sits in that domain.

**Architecture:** Pure function `suggest_next()` in `stats_service.py` returns a small dataclass. GUI `engine.py` wraps it and loads the lab. `MainWindow` already has `navigate_practice_weakest_domain`. Add `start_suggested_lab`. No new persistence tables.

**Tech Stack:** SQLAlchemy stats, PySide6, pytest, pytest-qt.

---

### Task 1: Engine suggestion API

**Files:**
- Modify: `src/openboson/stats_service.py`
- Modify: `tests/test_stats_service.py`

- [ ] **Step 1: Write failing tests**

```python
from openboson import stats_service
from openboson.netsim.lab_loader import load_lab


def test_suggest_next_prefers_weak_domain_practice_when_no_labs_match(fake_engine, exam_bank):
    sess = ExamSession.create(exam_bank, mode=ExamMode.EXAM)
    for q in sess.questions:
        sess.submit_answer(q.id, _wrong_answer(q), grade_now=True)
    stats_service.save_exam_result(sess, score_exam(sess))
    suggestion = stats_service.suggest_next(cert="ccna")
    assert suggestion is not None
    assert suggestion.kind in {"practice", "lab"}
    assert suggestion.topic_code
    assert suggestion.domain_prefix


def test_suggest_next_can_return_matching_gold_lab(fake_engine, exam_bank, lab):
    # Fail exams so domain 2 is weak if sample bank allows; otherwise skip if
    # no overlap. Bind explicitly:
    suggestion = stats_service.suggest_next(
        cert="ccna",
        labs=[lab],
        weak_prefix=lab.topic_code.split(".")[0],
    )
    assert suggestion.kind == "lab"
    assert suggestion.lab_id == lab.lab_id
```

Prefer a real API without `weak_prefix` override if you can seed answers on a topic that matches `ccna_branch_office_access` (`2.1`). If the sample bank has no `2.x` questions, pass `labs=` and compute weak domain from saved answers that you tag — keep the test on `isolated_home` / `fake_engine`.

Dataclass (add next to `DomainAggregate`):

```python
@dataclass
class StudySuggestion:
    kind: str  # "practice" | "lab"
    title: str
    domain_prefix: str
    topic_code: str | None = None
    lab_id: str | None = None
    cert_tag: str | None = None
```

```python
def suggest_next(
    cert: str | None = None,
    *,
    labs: list | None = None,
) -> StudySuggestion | None:
    weak = weak_domains(cert=cert, limit=1)
    if not weak:
        return None
    domain = weak[0]
    prefix = domain.domain_prefix.rstrip(".")
    catalog = labs
    if catalog is None:
        from openboson.registry import get_registry

        catalog = get_registry().labs()
    matches = [
        lab
        for lab in catalog
        if (not cert or cert in [t.lower() for t in lab.cert_tags] or (cert == "ccna" and "ccna" in lab.cert_tags))
        and str(lab.topic_code).split(".")[0] == prefix
        and getattr(lab, "lab_tier", None) is not None
        and lab.lab_tier.value == "gold"
    ]
    if matches:
        lab = sorted(matches, key=lambda L: L.lab_id)[0]
        return StudySuggestion(
            kind="lab",
            title=f"Lab: {lab.title}",
            domain_prefix=prefix,
            topic_code=lab.topic_code,
            lab_id=lab.lab_id,
            cert_tag=domain.cert_tag or cert,
        )
    return StudySuggestion(
        kind="practice",
        title=f"Practice domain {prefix}",
        domain_prefix=prefix,
        topic_code=prefix,
        cert_tag=domain.cert_tag or cert,
    )
```

Do not import Qt here.

- [ ] **Step 2: Run** `python -m pytest tests/test_stats_service.py::test_suggest_next_can_return_matching_gold_lab -v` — FAIL then PASS.

- [ ] **Step 3: Commit** `Suggest a gold lab or practice set from the weakest domain.`

---

### Task 2: GUI engine + main window navigation

**Files:**
- Modify: `src/openboson/gui/engine.py`
- Modify: `src/openboson/gui/main_window.py`
- Test: `tests/gui/test_stats_page.py` or new `tests/gui/test_study_loop.py`

```python
def next_study_suggestion(cert: str | None = None):
    from openboson import stats_service as svc

    return svc.suggest_next(cert=cert)
```

Reuse existing `get_lab_by_id` in `src/openboson/gui/engine.py` (loads registry labs, returns `LabBank | None`). Do not add a second lookup.

`MainWindow.start_lab_by_id(lab_id: str)`:

```python
def start_lab_by_id(self, lab_id: str) -> None:
    lab = engine.get_lab_by_id(lab_id)
    if lab is None:
        return
    self.start_lab_from_list(lab)
```

`MainWindow.apply_suggestion(suggestion)`:

- `practice` → `navigate_practice(cert=..., topic_code=suggestion.domain_prefix)`
- `lab` → `start_lab_by_id(suggestion.lab_id)`

pytest-qt: create MainWindow, monkeypatch `suggest_next` to return a lab suggestion, click the CTA, assert `visible_page_label() == "Lab"`.

- [ ] Commit `Wire study suggestions into the main window.`

---

### Task 3: Stats page + home CTA

**Files:**
- Modify: `src/openboson/gui/pages/stats_page.py`
- Modify: `src/openboson/gui/pages/__init__.py` (home dashboard)

After weak-domain bars, add a button `QPushButton` text `Continue: {suggestion.title}` objectName `suggestNextBtn`. Connect to a callback `set_on_suggestion` same pattern as `set_on_custom_exam`.

Home dashboard already builds CTA cards. Add a card when `suggest_next()` is not None.

- [ ] `python -m pytest tests/gui/test_stats_page.py tests/gui/test_lab_flow.py tests/test_stats_service.py -q`

- [ ] Commit `Offer a one-click next lab or practice set on Stats and Home.`

---

### Task 4: Exit

- [ ] No explanations UI. No new exam modes.
- [ ] Next: `2026-09-03-pbq-sim-items.md` (can parallelize with platform).
