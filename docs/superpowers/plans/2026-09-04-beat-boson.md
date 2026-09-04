# Beat Boson — Master Orchestration Plan

> **For agentic workers:** Orchestrator runs this file. Child plans are executed
> by isolated implementers, then a Boson-comparison reviewer, then a fix loop.
> REQUIRED: subagent-driven-development **plus** the bar in
> `docs/superpowers/specs/2026-09-04-beat-boson-bar.md`.
> Every implementer prompt starts with a **GOAL** block. Do not report the
> product complete until every aspect gate in the bar is green.

**Goal:** Make OpenBoson a better CCNA study product than Boson ExSim-Max used
alone, by teaching, honest labs, a study loop, and premium presence — not by
cloning Network Designer or 85 labs.

**Architecture:** Keep engine Qt-free. GUI via `gui/engine.py`. Deepen OpenIOS
only where `verify.ping` / `verify.show` would otherwise lie. Copy the ACL/NAT
pattern in `LabWorld`. Content stays YAML. Worktree-isolated implementers per
aspect; merge only after the Boson reviewer says the aspect gate holds.

**Tech Stack:** Python 3.11+, Pydantic v2, SQLAlchemy 2.0, PySide6, pytest /
pytest-qt, ruff, YAML labs/pools.

---

## Where we are (do not redo)

| Gate | Status |
|------|--------|
| Gold labs ≥20, total ≥25, ENCOR gold ≥3 | Met |
| CCNA ≥12/leaf ≥636; ENCOR ≥15/leaf ≥405 | Met |
| Honest NAT path (inside PC → outside needs PAT) | **Shipped** (`test_nat_path.py`, `_nat_blocks_inside_to_outside`) |
| ExSim custom exams, pause/resume, exports | Shipped |
| Lab console polish v0.4.1 | Shipped |
| Practice/review explanations | **Missing** (policy reversed by this plan) |
| Honest DHCP / PortFast / EtherChannel ping | **Missing** (commands exist; packet path ignores them) |
| `suggest_next()` study loop | **Missing** |
| Premium presence / first-run | **Missing** |
| Template explanation ban | **Missing** (pools still contain the phrase) |
| Network Designer / pack store / ENARSI | Out of scope |

NAT child plan `2026-09-03-honest-nat-path.md` is **done**. Do not re-implement it.
Mark remaining NAT tasks complete when editing that file.

---

## Orchestration protocol (every aspect)

```
GOAL → implementer (worktree) → tests → Boson reviewer (read-only, cwd=worktree)
     → if beats_boson false: resume implementer with gaps
     → merge to feat/beat-boson
```

1. Implementer prompt **must** begin with:

   ```
   # GOAL
   <one sentence from the aspect gate>
   You are not done until this GOAL is true and tests named in the child plan pass.
   Compare your result to Boson on this aspect. If Boson would still win, keep iterating.
   ```

2. Boson reviewer is adversarial. Default `beats_boson=false`. Require file+test
   evidence. Empty findings after reading code is allowed; empty findings without
   reading code is invalid.

3. Independent aspects run in parallel worktrees. Shared files
   (`world.py`, `shell.py`, `device.py`, `host.py`) are **sequential**:
   DHCP → STP/EC → gold lab tickets.

4. Do not push `v*` tags. Do not commit `.cursor/` or `IDEA.md`.

---

## Child plans (execute in this order)

| # | File | Aspect | Parallel with | Exit (Boson gate) |
|---|------|--------|---------------|-------------------|
| 0 | this file + bar spec | sequencing | — | team follows bar |
| 1 | `2026-09-03-honest-nat-path.md` | Believe/NAT | — | **DONE** |
| 2 | `2026-09-04-teaching-explanations.md` | Teach | 3, 4, 5, 6 | Check+review show teaching; exam mode silent |
| 3 | `2026-09-03-study-loop.md` | Coach | 2, 4, 5, 6 | Home/Stats CTA starts practice or gold lab |
| 4 | `2026-09-03-honest-dhcp.md` | Believe/DHCP | 2, 3, 5, 6 | renew then ping; no IP cannot ping |
| 5 | `2026-09-04-explanation-quality.md` | Teach/content | 2, 3, 4, 6 | template phrase banned; ≥24 flagship items |
| 6 | `2026-09-04-premium-presence.md` | Presence | 2, 3, 4, 5 | QSS density + first-run; no dashboard CTA theft |
| 7 | `2026-09-03-honest-stp-etherchannel.md` | Believe/L2 | after 4 | PortFast + EC change ping |
| 8 | `2026-09-03-gold-lab-tickets.md` | Believe/catalog | after 7 | four feature labs fail-before/pass-after |
| 9 | `2026-09-03-pbq-sim-items.md` | Teach/sims | after 8 | ≥5% only when gold labs exist to grade |
| 10 | `2026-09-03-v1-platform.md` | Trust | anytime after 0 | `openios-vs-ios.md` + first-run if not in 6 |

Wave 1 (parallel worktrees): **2, 3, 4, 5, 6**.
Wave 2 (after DHCP merged): **7 then 8**.
Wave 3: **9, 10** leftover.

---

## File ownership (avoid collisions)

| Aspect | Owns |
|--------|------|
| Teaching UI | `gui/pages/practice_question_page.py`, `exam_review_page.py`, optional `gui/widgets/teaching_feedback.py`, `tests/gui/test_exam_flow.py` |
| Study loop | `stats_service.py`, `gui/engine.py`, `gui/pages/__init__.py` (Dashboard), `gui/pages/stats_page.py`, `gui/main_window.py` navigation only, `tests/test_stats_service.py` |
| DHCP | `netsim/ios/device.py` (DhcpPool), `shell.py`, `host.py`, `world.py` only as needed, `tests/netsim/test_dhcp_path.py` |
| Explanation quality | `content/questions/**`, `scripts/assemble_question_pools.py` run, `tests/exsim/test_content_pools.py` template ban, `docs/content-authoring.md` |
| Presence | `gui/styles.qss`, `gui/styles_light.qss`, first-run modal in `main_window.py` **only if study-loop agent has not added it** — prefer a small `#FirstRun` dialog class in a new `gui/widgets/first_run.py` |
| STP/EC | same IOS files as DHCP — **after DHCP merge** |

Presence must not restyle by rewriting Dashboard Python. Study loop must not dump
inline `setStyleSheet` on the whole page.

---

## Non-negotiable rules

1. TDD. Failing test first for engine work.
2. Engine stays Qt-free.
3. No copyrighted dumps. Original wording only.
4. Do not widen `grade_task` / `submit_task` off `str`.
5. Gold labs must be able to fail on live verify, not `require:` alone.
6. Line length 100, ruff, pytest after each task.
7. YAGNI packet models (documented lies OK; silent lies not OK).
8. Work on `feat/beat-boson-*` branches in worktrees.

---

## Definition of done (product)

All aspect gates in `2026-09-04-beat-boson-bar.md` are green, `pytest -q` passes
on the merged tree, and a Boson-comparison reviewer for the **whole product**
answers: a CCNA candidate is better served by OpenBoson than by ExSim-Max alone.

Until that whole-product review is true, the orchestrator keeps iterating.
Do not tell the user the product is “better than Boson” without that review
plus test evidence.
