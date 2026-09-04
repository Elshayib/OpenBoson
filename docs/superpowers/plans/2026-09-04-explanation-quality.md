# Explanation Quality Implementation Plan

> **For agentic workers:** Isolated to `content/questions/`, assembled pools,
> `tests/exsim/test_content_pools.py`, and `docs/content-authoring.md`.
> Do not change GUI (that is the teaching-explanations plan).

**Goal:** Ban template distractor copy and ship ≥24 flagship CCNA items
(4 per domain 1–6) whose wrong-choice reasons are specific enough that Boson
would not embarrass them.

**Architecture:** Author in `content/questions/ccna/domain-{1..6}.yaml`. Run
`python scripts/assemble_question_pools.py` so `data/demo_banks/` matches.
CI forbids the template phrase in assembled YAML.

**Tech Stack:** YAML, pytest, existing assemble script.

---

### Task 1: CI ban on template rationales

**Files:**
- Modify: `tests/exsim/test_content_pools.py`

```python
_TEMPLATE_PHRASES = (
    "does not describe the intended use",
    "does not meet the requirement stated in the stem",
    "this is the correct answer for the stem",
)


def test_explanations_are_not_templates(ccna_bank, encor_bank):
    bad: list[str] = []
    for q in (*ccna_bank.questions, *encor_bank.questions):
        blob = " ".join(
            [
                q.explanation or "",
                *(c.rationale or "" for c in (q.choices or [])),
            ]
        ).lower()
        if any(p in blob for p in _TEMPLATE_PHRASES):
            bad.append(q.id)
    assert bad == [], f"template explanations: {bad[:20]}"
```

- [ ] Run test — FAIL on current pools.
- [ ] Do **not** weaken the assertion. Fix content instead.

---

### Task 2: Rewrite until the test passes + flagship depth

For every failing id, rewrite `explanation` so:

- The correct choice is justified with a protocol, command, or numeric reason.
- Each wrong choice names the misconception (e.g. “64 counts the network and
  broadcast addresses” not “64 is incorrect”).
- Original wording only. No Boson/Cisco dump text.

Also pick **4 questions per CCNA domain 1–6** (ids listed in a comment at the
top of each shard or a short `content/questions/ccna/FLAGSHIP.md` list) and
make those the teaching showcase (difficulty 3–5, specific distractors).

Then:

```
python scripts/assemble_question_pools.py
python -m pytest tests/exsim/test_content_pools.py -v
```

If ENCOR volume is huge, fix every template hit — the test covers both banks.

- [ ] Commit `content: ban template rationales; flagship CCNA explanations`

Boson gate: no shipped item uses generator filler; a reviewer sampling the
24 flagship stems would rather study these than a free dump site.
