# OpenBoson — Agent Guide

OpenBoson is an open-source, fully-local study platform for network engineers preparing for CCNA/CCNP. It combines Boson ExSim-style practice exams and Boson NetSim-style guided labs with a Cisco IOS CLI simulator, built as a single Python desktop app.

## Quick reference

| Item | Value |
|------|-------|
| Language | Python 3.11+ |
| GUI | PySide6 (Qt for Python), dark-first theme |
| Persistence | SQLite via SQLAlchemy 2.0 |
| Content | YAML question banks and lab definitions |
| CLI | `openboson gui`, `openboson serve --port 0` |
| Tests | `pytest` (unit + pytest-qt for GUI) |
| Lint | `ruff check .`, `ruff format .`, `mypy src/openboson` |

## Architecture

```
src/openboson/
├── cli.py              # Click CLI entrypoint
├── config.py           # Settings, data_dir (~/.openboson/)
├── db.py / models.py   # SQLAlchemy ORM + persistence
├── bank_schema.py      # Pydantic models for exam banks
├── bank_loader.py      # YAML exam bank loader
├── stats_service.py    # User stats and weak-area analytics
├── server.py           # FastAPI app (optional headless layer)
├── exsim/              # Practice exam engine
│   ├── session.py      # Exam session state machine
│   ├── scoring.py      # Answer grading and domain breakdown
│   └── router.py       # FastAPI endpoints
├── netsim/             # Lab simulator engine
│   ├── lab_schema.py   # Pydantic models for labs
│   ├── lab_loader.py   # YAML lab loader
│   ├── grader.py       # Config-comparison grading
│   ├── session.py      # Lab session state machine
│   ├── router.py       # FastAPI endpoints
│   └── ios/            # OpenIOS CLI simulator (shell, device, world)
└── gui/                # PySide6 desktop UI
    ├── app.py          # QApplication bootstrap
    ├── engine.py       # In-process bridge to engine modules
    ├── main_window.py  # Sidebar + QStackedWidget shell
    ├── pages/          # Screen implementations
    └── widgets/        # Reusable UI components
```

The GUI talks to the engine in-process via `gui/engine.py` (not over HTTP in normal use). The FastAPI layer exists for headless testing and future integrations.

## Content layout

```
data/
├── demo_banks/         # Shipped demo exam YAML files
└── demo_labs/          # Shipped demo lab YAML files
```

All questions and labs must be tagged with CCNA 200-301 v1.1 topic codes (e.g. `1.1`, `3.2.a`). Never add copyrighted exam dumps or proprietary Boson content — only original demo/community material.

## Development workflow

1. Install editable: `pip install -e ".[all]"`
2. Run tests: `pytest -v`
3. Run GUI: `openboson gui`
4. Run server (optional): `openboson serve --port 9876`

When implementing features, follow the task plan in `.cursor/plans/2026-07-27_OpenBoson_ExSim_NetSim_v1.md`. Work task-by-task, run relevant tests after each change, and keep diffs focused.

## Implementation status (as of v0.1.0)

**Done:**
- Tasks 1–12: Full scaffold, ExSim engine + GUI, NetSim engine + GUI
- Task 13 (partial): Stats page and `stats_service.py` (no separate analytics module)
- Task 16 (partial): Settings page with data dir, exam mode, theme toggle
- OpenIOS: Real CLI lab simulator (`netsim/ios/`) beyond original plan scope

**Not yet done:**
- Task 14: Hot-loadable bank/lab registry
- Task 15: CI workflow and Makefile
- Task 16 (packaging): PyInstaller installer scripts
- Network Designer (drag-drop topology builder)
- Real packet simulation (intentionally deferred)

## Conventions

- Use Pydantic v2 for all YAML schema validation.
- Keep engine logic pure Python — no Qt imports outside `gui/`.
- GUI pages live in `gui/pages/`, reusable widgets in `gui/widgets/`.
- Style with `gui/styles.qss`; avoid inline styles unless necessary.
- Write tests alongside new engine logic; use `pytest-qt` for widget tests.
- Line length 100 (ruff). Target Python 3.11.

## Key docs

- `README.md` — user-facing overview and quick start
- `.cursor/plans/2026-07-27_OpenBoson_ExSim_NetSim_v1.md` — full implementation plan
- `IDEA.md` — original project idea
