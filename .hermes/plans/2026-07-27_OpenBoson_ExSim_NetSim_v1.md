# OpenBoson — ExSim + NetSim Implementation Plan

> **For Hermes:** Use `subagent-driven-development` to implement this plan task-by-task.

**Goal:** Build an open-source, fully-local, rich GUI study platform that combines Boson ExSim-style practice exams and Boson NetSim-style guided labs / network simulator, focused first on CCNA 200-301 v1.1 topics.

**Architecture:** A single Python desktop app powered by PySide6 for the GUI and a Python engine for question-bank parsing, session scoring, lab grading, and simulation orchestration. The GUI loads banks, drives exam/lab sessions, and renders results using Qt widgets and charts. Data persists locally in SQLite.

**Tech Stack:** Python 3.11+, PySide6, Pydantic v2, PyYAML, SQLite via SQLAlchemy 2.0, pytest, Qt charts via PyQtGraph or QtCharts. An optional FastAPI/uvicorn HTTP layer is available for headless use and automated testing.

**License:** MIT. Content is user/community-provided; the repo ships only a small demo question bank and demo labs.

---

## Current Context & Standards

### CCNA 200-301 v1.1 Official Domains (Cisco source, valid until 2027-02-02)
- 1.0 Network Fundamentals — 20%
- 2.0 Network Access — 20%
- 3.0 IP Connectivity — 25%
- 4.0 IP Services — 10%
- 5.0 Security Fundamentals — 15%
- 6.0 Automation and Programmability — 10%

Each domain has numbered subtopics (1.1, 1.1.a, etc.). The app must support tagging every question and lab by precise topic code.

### Cisco question formats to support
- Multiple-choice single answer
- Multiple-select multiple answers
- Drag-and-drop matching / reordering
- Sim / Simlet / PBQ placeholders (CLI output interpretation, topology inspection)

### Boson NetSim features to support (eventual parity)
- 85+ guided labs mapped to CCNA topics
- Network Designer (drag-drop topology builder)
- Lab grading by configuration comparison
- Progress tracking

---

## Phase 1: Foundation (must work before any feature work)

### Task 1: Repository scaffold

**Objective:** Create a clean repo layout and commit the initial structure.

**Files:**
- Create: `README.md`
- Create: `LICENSE` (MIT)
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `src/openboson/__init__.py`
- Create: `src/openboson/gui/__init__.py`

**Steps:**
1. Write root README with project goal, architecture diagram in prose, and contribution guide outline.
2. Add MIT `LICENSE`.
3. Add `.gitignore` for Python, OS files, PyInstaller build artifacts, and SQLite files.
4. Create `pyproject.toml`:
   - `[project] name = "openboson"`
   - `requires-python = ">=3.11"`
   - Dependencies: `pyside6>=6.6`, `pydantic>=2`, `pyyaml`, `click`, `sqlalchemy>=2`, `pyqtgraph`
   - Dev dependencies: `pytest`, `pytest-qt`, `ruff`, `mypy`
   - `[project.scripts] openboson = "openboson.cli:main"`
5. Create `src/openboson/__init__.py` exporting `__version__ = "0.1.0"`.
6. Create `src/openboson/gui/__init__.py` empty for now.
7. Commit.

**Verification:**
- `git ls-files` shows the expected files.
- `python -c "import openboson; print(openboson.__version__)"` prints `0.1.0`.

---

### Task 2: Python engine skeleton + CLI

**Objective:** Build the Python entrypoint and a local HTTP server skeleton.

**Files:**
- Create: `src/openboson/api.py`
- Create: `src/openboson/cli.py`
- Create: `src/openboson/config.py`
- Create: `src/openboson/server.py`
- Create: `tests/test_smoke.py`

**Steps:**
1. Define `config.py` with `settings` object, `data_dir()` defaulting to `~/.openboson/`, and `DEBUG=False`.
2. Implement `server.py` with FastAPI app and `GET /health -> {"status":"ok"}`.
3. Implement `cli.py` with Click command:
   ```bash
   openboson serve --port 0
   ```
   `--port 0` binds any free port and prints the chosen port to stdout.
   Also add `openboson --version`.
4. Write `test_smoke.py`:
   ```python
   from fastapi.testclient import TestClient
   from openboson.server import app

   def test_health():
       client = TestClient(app)
       resp = client.get("/health")
       assert resp.status_code == 200
       assert resp.json()["status"] == "ok"
   ```
5. Run `pytest tests/test_smoke.py -v`.
6. Commit.

**Verification:**
- `pytest tests/test_smoke.py -v` passes.
- `python -m openboson.cli serve --port 9876` starts and responds to `curl http://127.0.0.1:9876/health`.

---

### Task 3: SQLite persistence layer

**Objective:** Define core tables and a repository pattern.

**Files:**
- Create: `src/openboson/db.py`
- Create: `src/openboson/models.py`
- Create: `tests/test_db.py`

**Steps:**
1. In `db.py`, create SQLAlchemy 2.0 declarative models in `OrmBase`.
   Tables:
   - `users` (id, display_name, created_at)
   - `exams` (id, title, exam_code, version, provider, metadata JSON)
   - `questions` (id, exam_id, topic_code, type, stem JSON, choices JSON, correct_answer JSON, explanation, difficulty, created_at)
   - `exam_sessions` (id, user_id, exam_id, mode, started_at, finished_at, score, passed)
   - `user_answers` (id, session_id, question_id, answer JSON, is_correct, time_spent_seconds)
   - `lab_sessions` (id, user_id, lab_id, started_at, finished_at, status, score)
   - `lab_steps` (id, lab_session_id, step_index, expected_config, submitted_config, is_correct, feedback)
2. Add `get_engine()` and `init_db()` that creates tables without Alembic.
3. In `test_db.py`, write tests for `init_db` and inserting/selecting one user, one exam, one session.
4. Run tests.
5. Commit.

**Verification:**
- `pytest tests/test_db.py -v` passes.
- A file appears in a temp directory after `init_db`.

---

### Task 4: Question-bank YAML schema and loader

**Objective:** Human-readable, diff-friendly question files covering all Cisco question types.

**Files:**
- Create: `src/openboson/bank_schema.py`
- Create: `src/openboson/bank_loader.py`
- Create: `tests/test_bank_loader.py`
- Create: `data/demo_banks/ccna_200_301_v1.1_demo.yaml`

**Steps:**
1. Define Pydantic v2 models in `bank_schema.py`:
   - `Choice` (id, text, media_url optional)
   - `Question` with `type` enum: `single_choice`, `multiple_choice`, `drag_match`, `ordered_list`, `sim` (placeholder)
   - `Question.correct` as a discriminated union.
   - `ExamBank` (title, code, version, description, topics, pass_score, time_limit_minutes, questions)
2. Implement `bank_loader.py` `load_exam_bank(path_or_stream) -> ExamBank` with YAML parsing and validation.
3. Create a demo bank with 5–10 questions spanning:
   - Network Fundamentals (subnetting single choice)
   - Network Access (switching multi-select)
   - IP Connectivity (OSPF ordering)
   - IP Services (DHCP drag-match)
   - Security (ACL sim/pbq placeholder)
   - Automation (NETCONF/YANG single choice)
4. Write tests:
   - Load demo bank, assert question count and valid types.
   - Test invalid YAML raises `ValidationError`.
5. Run tests.
6. Commit.

**Verification:**
- `pytest tests/test_bank_loader.py -v` passes.
- Demo bank loads without errors.

---

## Phase 2: ExSim Practice Exam Module

### Task 5: Exam session domain logic

**Objective:** Pure Python state machine for an exam session.

**Files:**
- Create: `src/openboson/exsim/session.py`
- Create: `src/openboson/exsim/scoring.py`
- Create: `tests/exsim/test_session.py`
- Create: `tests/exsim/test_scoring.py`

**Steps:**
1. `session.py`:
   - `ExamSession` dataclass with `session_id`, `exam`, `questions` (shuffled copy), `current_index`, `answers: dict[question_id, UserAnswer]`, `bookmarked`, `mode`.
   - Methods: `submit_answer(question_id, answer)`, `mark_for_review(question_id)`, `next()`, `previous()`, `finish()`.
2. `scoring.py`:
   - `grade_answer(question, user_answer) -> bool` for all supported types.
   - `score_exam(session) -> ExamResult` — total, per-domain breakdown, pass/fail.
3. Tests:
   - Single-select correct yields 1 point.
   - Multiple-select requires exact match.
   - Partial credit config for multiple-select.
   - Drag-match requires all pairs correct.
   - Domain breakdown matches weight logic.
4. Commit.

**Verification:**
- `pytest tests/exsim/ -v` passes.

---

### Task 6: Engine API endpoints for ExSim

**Objective:** HTTP/JSON-RPC surface for headless use and for the GUI layer.

**Files:**
- Create: `src/openboson/exsim/router.py`
- Modify: `src/openboson/server.py` to include the router.
- Create: `tests/exsim/test_api.py`

**Steps:**
1. Endpoints (FastAPI router), mounted at `/api/v1`:
   - `GET /exams` — list loaded exams.
   - `POST /exams/{exam_id}/sessions` — create new session; return session id + first question (without correct answer).
   - `GET /sessions/{session_id}/questions/{index}` — current question for display.
   - `POST /sessions/{session_id}/answers` — submit answer for current question.
   - `POST /sessions/{session_id}/bookmark` — toggle bookmark.
   - `POST /sessions/{session_id}/finish` — grade and return `ExamResult`.
   - `GET /sessions/{session_id}/review` — full question list with user answers and explanations.
2. Tests:
   - Full happy path: create session -> answer all -> finish -> review.
   - Ensure `correct` field is never leaked in question responses.
3. Commit.

**Verification:**
- `pytest tests/exsim/test_api.py -v` passes.
- Manual `curl` sequence works end to end.

---

### Task 7: PySide6 GUI shell

**Objective:** Boot a great-looking desktop UI with a main window, navigation sidebar, and dark-first theme.

**Files:**
- Create: `src/openboson/gui/app.py`
- Create: `src/openboson/gui/main_window.py`
- Create: `src/openboson/gui/styles.qss`
- Create: `src/openboson/gui/__main__.py`
- Modify: `pyproject.toml` if needed to add `openboson-gui` script.

**Steps:**
1. Create `app.py`:
   - `QApplication` with org/app name, dark palette, custom icon placeholder.
   - Start local service: either run the FastAPI server in a background thread or use in-process Python calls directly.
   - Exit gracefully on window close (stop server thread if running).
2. Create `main_window.py`:
   - `QMainWindow` with sidebar list (Dashboard, Exams, Labs, Stats, Settings) and a `QStackedWidget` for content pages.
   - Placeholder pages for each section.
3. Create `styles.qss` with a modern dark theme matching a Boson-like deep-blue accent.
4. Create `__main__.py` so the GUI launches with `python -m openboson.gui` or `openboson gui`.
5. Add a smoke test using `pytest-qt` that instantiates `MainWindow` and verifies the stack has the expected pages.
6. Commit.

**Verification:**
- `openboson gui` opens a window with sidebar and stacked pages.
- `pytest tests/gui/test_main_window.py -v` passes.

---

### Task 8: ExSim GUI screens

**Objective:** Implement the practice-exam UI end-to-end.

**Files:**
- Create: `src/openboson/gui/pages/exam_list_page.py`
- Create: `src/openboson/gui/pages/exam_session_page.py`
- Create: `src/openboson/gui/pages/exam_review_page.py`
- Create: `src/openboson/gui/pages/exam_result_page.py`
- Create: `src/openboson/gui/widgets/question_card.py`
- Create: `src/openboson/gui/widgets/answer_options.py`
- Create: `src/openboson/gui/widgets/timer_bar.py`

**Steps:**
1. `exam_list_page.py`: list of exams as cards with mode selection (Study / Timed / Custom).
2. `exam_session_page.py`:
   - Question stem in scrollable card using `QTextBrowser` with basic HTML/Markdown.
   - Answer widget varies by question type:
     - `single_choice` → `QRadioButton` group
     - `multiple_choice` → `QCheckBox` list
     - `drag_match` → two-column drag/drop list (or simpler pair assignment for MVP)
     - `ordered_list` → numbered list editor
     - `sim` → placeholder text explaining PBQ not yet implemented
   - Navigation buttons: previous, next, finish, bookmark, mark review.
   - Timer bar at top.
3. `exam_review_page.py`: filter combo (all / incorrect / bookmarked) + question list showing correct answer, user answer, explanation.
4. `exam_result_page.py`: score label, pass/fail banner, per-domain bar chart (PyQtGraph or QProgressBar), retake/review buttons.
5. Run a full demo exam in the GUI and verify navigation, scoring, review, results.
6. Commit.

**Verification:**
- GUI can start demo exam, answer questions, finish, view results, and review.
- `pytest-qt` tests verify widgets update on answer submission.

---

## Phase 3: NetSim Network Simulator Module

### Task 9: Lab YAML schema and loader

**Objective:** Define the data model for guided labs and the Network Designer metadata.

**Files:**
- Create: `src/openboson/netsim/lab_schema.py`
- Create: `src/openboson/netsim/lab_loader.py`
- Create: `tests/netsim/test_lab_loader.py`
- Create: `data/demo_labs/ccna_subnetting_lab.yaml`

**Steps:**
1. Pydantic models:
   - `Device` (name, type: router/switch/ap/firewall, interfaces, base_config)
   - `Topology` (devices, links)
   - `LabTask` (instructions, expected_config_snippet, grading_rules)
   - `LabBank` (title, topic_code, difficulty, objectives, topology, tasks, solution_config)
2. Loader similar to exam banks.
3. Demo lab: "Subnetting a /26 into two departments" with a small topology (2 PCs, 1 router, 1 switch).
4. Tests:
   - Load demo lab.
   - Validate topology connectivity.
5. Commit.

**Verification:**
- `pytest tests/netsim/test_lab_loader.py -v` passes.

---

### Task 10: Lab grading engine (Phase 1: config comparison)

**Objective:** Grade a user’s configuration text against expected commands or configuration state.

**Files:**
- Create: `src/openboson/netsim/grader.py`
- Create: `tests/netsim/test_grader.py`

**Steps:**
1. Implement `compare_config_lines(submitted: str, expected: str) -> GradingResult`:
   - Normalize Cisco IOS config lines (strip whitespace, ignore `!` comments, sort where order-independent).
   - Check required presence, check forbidden lines.
   - Return per-task `score`, `missing_lines`, `extra_lines`, `feedback`.
2. Support hostname, interface IP/mask, VLAN, static route, SSH, NAT overload, ACL rules for MVP.
3. Tests:
   - Config with correct hostname and IP passes.
   - Missing static route flagged.
   - Extra forbidden command flagged.
4. Commit.

**Verification:**
- All grader tests pass.

---

### Task 11: NetSim API and lab session engine

**Objective:** Stateful lab session with instructions and grading.

**Files:**
- Create: `src/openboson/netsim/session.py`
- Create: `src/openboson/netsim/router.py`
- Modify: `src/openboson/server.py`
- Create: `tests/netsim/test_lab_session.py`

**Steps:**
1. `LabSession` state machine: current task index, submitted configs per task, graded results.
2. Endpoints (`/api/v1`):
   - `GET /labs` — list labs.
   - `POST /labs/{lab_id}/sessions` — start session.
   - `GET /labs/{lab_id}/topology` — topology for Network Designer.
   - `GET /lab-sessions/{session_id}/task` — current instructions.
   - `POST /lab-sessions/{session_id}/submit` — submit config and grade.
   - `POST /lab-sessions/{session_id}/finish` — final score.
3. Tests:
   - Start lab, submit correct config, assert 100%.
   - Submit wrong config, assert feedback contains "missing" lines.
4. Commit.

**Verification:**
- `pytest tests/netsim/ -v` passes.

---

### Task 12: NetSim UI screens

**Objective:** Lab browser, instruction panel, terminal-like config input, and topology canvas.

**Files:**
- Create: `src/openboson/gui/pages/lab_list_page.py`
- Create: `src/openboson/gui/pages/lab_session_page.py`
- Create: `src/openboson/gui/pages/lab_result_page.py`
- Create: `src/openboson/gui/widgets/topology_canvas.py`
- Create: `src/openboson/gui/widgets/terminal_input.py`
- Create: `src/openboson/gui/widgets/lab_task_panel.py`

**Steps:**
1. `lab_list_page.py`: cards showing title, topic, difficulty.
2. `lab_session_page.py`:
   - Left: `lab_task_panel.py` with instructions and step list.
   - Center: `terminal_input.py` (textarea styled like a Cisco terminal) to paste/type config.
   - Right: `topology_canvas.py` read-only SVG or `QPainter` view of devices and links.
   - Submit button runs grader and shows feedback inline.
3. `topology_canvas.py`: render devices as rounded rectangles, links as lines, device labels and hover tooltips with base interface names.
4. `lab_result_page.py`: total score, per-task breakdown, link to solution view.
5. Manual run of demo subnetting lab in GUI.
6. Commit.

**Verification:**
- GUI can load lab list, start demo lab, submit correct config, finish, view results.

---

## Phase 4: Cross-Cutting Features

### Task 13: User profiles and statistics

**Objective:** Track weak areas across both modules.

**Files:**
- Create: `src/openboson/analytics.py`
- Create: `src/openboson/gui/pages/dashboard_page.py`
- Create: `src/openboson/gui/pages/stats_page.py`

**Steps:**
1. Aggregates:
   - Exams taken, pass rate, average score over time.
   - Per-topic accuracy (weighted by domain).
   - Lab completion count and average score.
2. Engine endpoints:
   - `GET /users/{user_id}/stats`
   - `GET /users/{user_id}/weak-areas` returns top 5 topic codes with lowest accuracy.
3. Dashboard UI: recent activity + suggested next exam/lab based on weak areas.
4. Stats page: charts and a table.
5. Commit.

**Verification:**
- Tests for analytics functions pass.
- Dashboard renders stats after completing one exam in the GUI.

---

### Task 14: Question / lab bank registry

**Objective:** Make banks and labs discoverable and hot-loadable.

**Files:**
- Create: `src/openboson/registry.py`
- Create: `data/banks/.gitkeep`
- Create: `data/labs/.gitkeep`
- Modify: `README.md`

**Steps:**
1. Registry scans `data/banks/` and `data/labs/` at startup; loads valid YAMLs; skips invalid with warnings.
2. API endpoint `/api/v1/content/refresh` rescans.
3. README documents bank/lab format for contributors.
4. Commit.

**Verification:**
- Start engine with an extra exam file; it appears in `/exams`.
- Remove file; refresh makes it disappear.

---

## Phase 5: DevEx, Packaging, CI

### Task 15: Lint, type-check, tests, and formatting

**Objective:** Quality gates so community contributions stay clean.

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `Makefile`

**Steps:**
1. Python: `ruff format --check .`, `ruff check .`, `mypy src/openboson`, `pytest --cov=openboson --cov-report=term-missing`.
2. Add `pyproject.toml` config sections for ruff and mypy.
3. GitHub Actions matrix: ubuntu-latest, windows-latest.
4. Commit.

**Verification:**
- `make check` passes locally.
- CI workflow passes on push.

---

### Task 16: Packaging and installer

**Objective:** End users get a single installer, no Python setup required.

**Files:**
- Create: `scripts/build-windows.bat`
- Create: `scripts/build-linux.sh`
- Modify: `pyproject.toml`
- Create: `openboson.spec` (PyInstaller spec)

**Steps:**
1. Bundle the Python interpreter + deps + `src/openboson` with PyInstaller as `openboson.exe` / `openboson`.
2. Add a one-file or one-folder Windows `.msi`/`.exe` installer via optional `msix` or NSIS.
3. Ensure the executable reads `data/` from the bundled resources or next to the binary.
4. README install instructions.
5. Commit.

**Verification:**
- `pyinstaller openboson.spec` produces a runnable `dist/openboson/openboson.exe`.
- Installed/bundled app opens and loads the demo exam bank.

---

## Risks & Tradeoffs

1. **Real packet simulation** is intentionally deferred. NetSim Phase 1 is configuration grading only; Phase 2 will either embed GNS3/dynamips/Quagga or a custom Python simulator. Document this as a future roadmap.
2. **Copyright content.** We must never ship commercial Boson questions or Cisco exam dumps. All shipped content is original demo/community content tagged to the official blueprint.
3. **Performance.** YAML parsing all banks at startup is fine up to a few thousand questions; add lazy bank loading if it becomes slow.
4. **GUI choice.** PySide6 is heavier than a web GUI but easier to ship and build on a Windows machine without Rust. Later we can add a web frontend that talks to the same FastAPI server.

---

## Open Questions (non-blocking for MVP)

- Should the app bundle a default user automatically, or require creating a profile first? **Default: auto-create a default user on first launch.**
- Should custom exam mode allow filtering by topic and difficulty? **Default: yes.**
- Should we support importing existing formats (Anki, GIFT, CSV)? **Default: no for MVP, add later.**
- Should the GUI theme be configurable beyond dark/light? **Default: dark/light toggle only.**

---

## First executable milestone

After completing **Tasks 1–4 and 7**, the deliverable is:
- A PySide6 window opens.
- It can load the Python engine and demo exam bank.
- The dashboard/exam list is reachable from the UI.

This milestone validates the architecture before investing heavily in UI polish.
