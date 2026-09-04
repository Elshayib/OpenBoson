# PBQ / OpenIOS Sim Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. **Depends on:** honest NAT (and ideally DHCP) so sims that ping are real. Existing `type: sim` questions keep substring grading when `lab_id` is absent.

**Goal:** Sim questions with a `lab_id` are graded by applying the student’s config to that lab’s OpenIOS world and evaluating `verify` / `grading_rules`, not by string-contains on `expected_commands`. Blueprint can require a minimum number of sim items. Pool gate ≥5% only after enough original items exist.

**Architecture:** Extend `SimSpec` and `SimAnswer` with optional `lab_id` (Pydantic `extra=forbid` — additive optional fields only). `_grade_sim` branches: if `lab_id` set, load lab, `LabSession.create`, feed config via `_apply_blob` per device or combined running-config on the named device, then `check_all_tasks` / grade listed `task_ids`. GUI keeps a text editor for v1 (no full multi-tab console inside the exam card). Do not show explanations.

**Tech Stack:** Pydantic v2, OpenIOS LabSession, pytest.

---

### Task 1: Schema — optional lab_id on sim

**Files:**
- Modify: `src/openboson/bank_schema.py` (`SimSpec`, `SimAnswer`)
- Modify: `tests/exsim/test_scoring.py` or `tests/test_bank_loader.py`

```python
class SimSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instructions: str
    topology_ref: str | None = None
    expected_output: str | None = None
    lab_id: str | None = None
    task_ids: list[str] | None = None


class SimAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_config: str | None = None
    expected_commands: list[str] | None = None
    instructions: str | None = None
    lab_id: str | None = None  # duplicate allowed if YAML puts it under correct; prefer sim.lab_id
```

Keep existing sample_bank `q5` loading.

- [ ] Test: load `tests/fixtures/sample_bank.yaml` sim question still validates.
- [ ] Test: a dict with `sim.lab_id = "ccna_branch_office_access"` validates.
- [ ] Commit `Allow sim questions to reference a bundled lab id.`

---

### Task 2: Grade via LabSession

**Files:**
- Modify: `src/openboson/exsim/scoring.py` (`_grade_sim`)
- Test: `tests/exsim/test_scoring.py`

```python
def _grade_sim(correct: SimAnswer, user_answer: Any, question: Question | None = None) -> bool:
    if isinstance(user_answer, dict):
        submitted_text = user_answer.get("config") or user_answer.get("submitted_config") or ""
    else:
        submitted_text = str(user_answer)

    lab_id = None
    task_ids = None
    if question is not None and question.sim is not None:
        lab_id = question.sim.lab_id
        task_ids = question.sim.task_ids
    lab_id = lab_id or getattr(correct, "lab_id", None)

    if not lab_id:
        expected_cmds = correct.expected_commands or []
        if not expected_cmds:
            return False
        submitted_lines = {line.strip() for line in submitted_text.splitlines() if line.strip()}
        return all(cmd.strip() in submitted_lines for cmd in expected_cmds)

    from openboson.registry import get_registry
    from openboson.netsim.session import LabSession

    lab = next((L for L in get_registry().labs() if L.lab_id == lab_id), None)
    if lab is None:
        return False
    sess = LabSession.create(lab)
    _feed_sim_config(sess, submitted_text)
    ids = task_ids or [t.id for t in lab.tasks]
    for i, task in enumerate(lab.tasks):
        if task.id not in ids:
            continue
        sess.goto(i)
        grade = sess.check_current_task()
        if not grade.is_correct:
            return False
    return True
```

Change `grade_answer` to pass `question` into `_grade_sim`.

`_feed_sim_config`: if the blob contains `! --- R1 ---` markers (same as `combined_running_config` / solution_config), split and feed each device like `LabSession._apply_base_configs`. If no markers, feed the current device / first router in config mode.

Failing test using `ccna_branch_office_access` t1 blob (R1 addressing) as user config, `task_ids: ["t1"]` — must be correct. Empty config — incorrect.

**Do not** change `grade_answer` signature in a way that breaks callers — add optional question already in `grade_answer(question, user_answer)`.

- [ ] Run `python -m pytest tests/exsim/test_scoring.py -v`
- [ ] Commit `Grade lab-linked sim questions through OpenIOS.`

---

### Task 3: One original lab-linked sim in the CCNA shard

**Files:**
- Modify: `content/questions/ccna/domain-4.yaml` (or domain matching NAT `4.1`)
- Run: `python scripts/assemble_question_pools.py`

YAML (original wording; do not copy Boson):

```yaml
- id: ccna-4-sim-pat-001
  type: sim
  topic_code: "4.1"
  difficulty: 4
  cert_tags: [ccna]
  stem: >
    PC1 (192.168.1.10/24) must reach 203.0.113.2 through R1. Configure PAT
    overload on R1 using list 1 and the outside interface.
  sim:
    instructions: >
      Use the NAT PAT Edge topology. Configure inside/outside and PAT, then
      paste R1's relevant configuration.
    lab_id: ccna_nat_pat_edge
    task_ids: [t1, t2, t3]
  correct:
    expected_commands:
      - ip nat inside
      - ip nat outside
  references:
    - CCNA exam topic 4.1
  provider: openboson
  license: MIT
  provenance: original
```

`expected_commands` remain as a fallback if lab load fails in tests that do not ship labs — still prefer lab grading.

- [ ] Assemble pools. `python -m pytest tests/exsim/test_content_pools.py -q`
- [ ] Commit `Add an original PAT sim item graded against the NAT gold lab.`

Do **not** flip a ≥5% gate until you have counted `type: sim` / total. Add the gate in `tests/exsim/test_content_pools.py` only when the ratio is already true:

```python
def test_sim_share_floor(ccna_bank):
    sims = [q for q in ccna_bank.questions if q.type.value == "sim"]
    assert len(sims) / len(ccna_bank.questions) >= 0.05
```

If the current ratio is below 5%, **leave the assert unwritten** and track the count in `docs/status.md` instead of failing CI.

---

### Task 4: Blueprint sampling (optional floor)

**Files:** `src/openboson/exsim/blueprint.py`, `tests/exsim/test_blueprint.py`

Add `min_sim_items: int = 0` on `ExamBlueprint`. After domain allocation, if `min_sim_items > 0`, ensure that many sampled questions have `type == SIM` (swap from remaining pool). Default 0 so existing 100-question CCNA blueprint does not break when the sim pool is thin.

When sim pool is large enough, set CCNA blueprint `min_sim_items=5` (5%).

- [ ] Tests for allocate/swap.
- [ ] Commit `Allow blueprints to reserve a minimum number of sim items.`

---

### Task 5: GUI copy only

**Files:** `src/openboson/gui/widgets/question_card.py`

If `q.sim and q.sim.lab_id`, placeholder text: `Paste the device configuration for lab {lab_id}...`. No in-exam topology canvas in this slice (YAGNI). Practice Check remains correct/incorrect.

- [ ] pytest-qt if a widget test exists; otherwise engine tests suffice.
- [ ] Exit. Next: `2026-09-03-v1-platform.md` or more sim items as content-only PRs.
