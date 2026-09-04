# Beat Boson — Master Orchestration Plan

> **For agentic workers:** Orchestrator runs this file. Child plans are executed
> by isolated implementers, then a Boson-comparison reviewer, then a fix loop.
> REQUIRED: subagent-driven-development **plus** the bar in
> `docs/superpowers/specs/2026-09-04-beat-boson-bar.md`.
> Every implementer prompt starts with a **GOAL** block. Core aspects **1–8 and
> Trust docs / first-run** shipped on `master` (`6228c39`, CI green). Remaining:
> PBQ (`2026-09-03-pbq-sim-items.md`) and v1 typed-core mypy.

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
| Gold labs ≥20, total ≥25, ENCOR gold ≥3 | **Met** |
| CCNA ≥12/leaf ≥636; ENCOR ≥15/leaf ≥405 | **Met** |
| Honest NAT / DHCP / PortFast / EtherChannel ping | **Shipped** (`test_nat_path.py`, `test_dhcp_path.py`, `test_stp_path.py`) |
| Gold NAT/DHCP/STP/EC fail-before / pass-after | **Shipped** (`test_gold_*_lab.py`) |
| Practice/review explanations; exam silent | **Shipped** (`TeachingFeedback`) |
| Template explanation CI ban + 24 flagship items | **Shipped** (typical `ccna-v05-*` items can still be thin) |
| `suggest_next()` study loop | **Shipped** |
| First-run + denser QSS | **Shipped** (some inline styles remain) |
| `docs/openios-vs-ios.md` | **Shipped** |
| Network Designer / pack store / ENARSI | Out of scope |
| ≥5% PBQ/sim items | **Not started** — `2026-09-03-pbq-sim-items.md` |
| Typed-core mypy expansion | **Not started** — `2026-09-03-v1-platform.md` Task 2+ |

---

## Orchestration protocol (every aspect)

```
GOAL → implementer (worktree) → tests → Boson reviewer (read-only, cwd=worktree)
     → if beats_boson false: resume implementer with gaps
     → merge to master (or a feat branch then FF)
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
| 0 | this file + bar spec | sequencing | — | **DONE** |
| 1 | `2026-09-03-honest-nat-path.md` | Believe/NAT | — | **DONE** |
| 2 | `2026-09-04-teaching-explanations.md` | Teach | — | **DONE** |
| 3 | `2026-09-03-study-loop.md` | Coach | — | **DONE** |
| 4 | `2026-09-03-honest-dhcp.md` | Believe/DHCP | — | **DONE** |
| 5 | `2026-09-04-explanation-quality.md` | Teach/content | — | **DONE** (flagships + CI ban; typical items still thinner than Boson) |
| 6 | `2026-09-04-premium-presence.md` | Presence | — | **DONE** (first-run + QSS; some inline styles remain) |
| 7 | `2026-09-03-honest-stp-etherchannel.md` | Believe/L2 | — | **DONE** |
| 8 | `2026-09-03-gold-lab-tickets.md` | Believe/catalog | — | **DONE** |
| 9 | `2026-09-03-pbq-sim-items.md` | Teach/sims | after 8 | **NEXT** ≥5% when content exists |
| 10 | `2026-09-03-v1-platform.md` | Trust | — | Task 1 + first-run **DONE**; typed-core mypy leftover |

Execute **9** next. Do not re-run 1–8.

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
8. Work on feature branches in worktrees; merge to `master` only after tests + ruff.

---

## Definition of done (product)

Core bar (teach UI, believe, coach, trust docs) is **met on `master`**. Whole-product
reviewer: a CCNA candidate using only OpenBoson is better served than ExSim-Max
alone. **Do not market “better explanations than Boson.”** Remaining: PBQ ≥5%,
typical-item editorial, typed-core mypy, Authenticode.
