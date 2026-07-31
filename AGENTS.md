# OpenBoson — Agent Guide

OpenBoson is an open-source, fully-local study platform for network engineers preparing for CCNA/CCNP. It combines Boson ExSim-style practice exams and Boson NetSim-style guided labs with a Cisco IOS CLI simulator, built as a single Python desktop app.

Practice blueprints and demo pools cover **CCNA 200-301 v1.1** and **CCNP ENCOR 350-401 v1.2**. Allowed topic codes live in `exsim/objectives.py` (Cisco public exam topics; refresh date **2026-07-31**).

## Quick reference

| Item | Value |
|------|-------|
| Language | Python 3.11+ |
| GUI | PySide6 (Qt for Python), dark-first theme |
| Persistence | SQLite via SQLAlchemy 2.0 |
| Content | YAML pools + CCNA 200-301 v1.1 / ENCOR 350-401 v1.2 blueprints |
| CLI | `openboson gui`, `openboson serve --port 0` |
| Tests | `pytest` (unit + pytest-qt for GUI) |
| Lint | `ruff check .`, `ruff format .`, `mypy src/openboson` |

## Architecture

```
src/openboson/
├── cli.py              # Click CLI entrypoint
├── config.py           # Settings, data_dir (~/.openboson/)
├── db.py / models.py   # SQLAlchemy ORM + persistence
├── bank_schema.py      # Pydantic models for exam banks / pools
├── bank_loader.py      # YAML bank loader + pool merge
├── stats_service.py    # User stats, practice attempts, analytics
├── server.py           # FastAPI app (optional headless layer)
├── exsim/              # Practice exam engine
│   ├── blueprint.py    # CCNA v1.1 / ENCOR v1.2 presets + sampling
│   ├── objectives.py   # Versioned allowed topic-code registries
│   ├── session.py      # Exam session (practice / exam modes)
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
├── demo_banks/         # Shipped question pool YAML (CCNA + ENCOR)
└── demo_labs/          # Shipped demo lab YAML files
```

All questions and labs must be tagged with topic codes (e.g. `1.1`) that exist in the matching objective map. Questions carry `cert_tags: [ccna]` and/or `[ccnp]`. Never add copyrighted exam dumps or proprietary Boson content — only original demo/community material.

Exam presentation for the GUI/API uses `QuestionPresentation.to_dict()` with public keys `choice_ids`, `ordered_items`, `left_items`, and `right_items`. Drag-match grading still uses left/right **text** pairs.

## Development workflow

1. Install editable: `pip install -e ".[all]"`
2. Run tests: `pytest -v`
3. Run GUI: `openboson gui`
4. Run server (optional): `openboson serve --port 9876`

When implementing features, work task-by-task, run relevant tests after each change, and keep diffs focused.

## Implementation status (as of v0.2.2)

**Shipped:** https://github.com/Elshayib/OpenBoson/releases/tag/v0.2.2 — see `docs/status.md` for handoff.

**Done:**
- ExSim engine + GUI (practice library pagination, blueprints, Check + rationales, keyboard drag-match)
- NetSim engine + GUI (OpenIOS, reset, per-device grading hooks)
- Hot-load registry (bundled + local + packs), content refresh API/Settings
- Stats weak-domain analytics + Dashboard/Practice deep links
- Settings: theme, logs/backups, updates card, content diagnostics
- Resource paths, logging, DB backups, typed settings store
- CI (Windows/Ubuntu), Makefile / `scripts/dev.ps1`, quality baseline
- Windows packaging: PyInstaller onedir, Inno script, release workflow
- Domain-sharded content pipeline; ≥500 CCNA / ≥400 ENCOR; ≥20 labs

**Next (v0.3 — see `docs/deferred-releases.md`):**
- Custom exams, pause/resume, exports, content scale, PBQs

**Later:**
- v0.4 NetSim depth · v0.5 Network Designer · v0.6 packs · v1.0 signed cross-platform

## Conventions

- Use Pydantic v2 for all YAML schema validation.
- Keep engine logic pure Python — no Qt imports outside `gui/`.
- GUI pages live in `gui/pages/`, reusable widgets in `gui/widgets/`.
- Style with `gui/styles.qss` / `styles_light.qss`; avoid inline styles unless necessary.
- Write tests alongside new engine logic; use `pytest-qt` for widget tests.
- Line length 100 (ruff). Target Python 3.11.
- Never commit `.cursor/`, `IDEA.md`, or other local agent/private notes.
- Public commit messages must be professional (repo is public).

## Key docs

- `docs/status.md` — current handoff / what’s next
- `README.md` — user-facing overview and quick start
- `docs/deferred-releases.md` — v0.3+ scope and gates
- `docs/quality-baseline.md` — CI / quality gates
- `docs/v020-beta-checklist.md` — optional Windows install verification
- `CHANGELOG.md` / `SUPPORT.md` / `PRIVACY.md`
