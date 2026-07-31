# OpenBoson

An open-source, fully-local study platform that combines Boson ExSim-style practice exams and Boson NetSim-style guided labs / network simulator for Cisco certifications.

Shipped practice content targets **CCNA 200-301 v1.1** and **CCNP ENCOR 350-401 v1.2**. Objective maps are taken from Cisco’s public exam topics (Learning Network / topics PDFs); registry refresh date: **2026-07-31** (see `src/openboson/exsim/objectives.py`).

## Status

**v0.2 Study Ready content targets are met in-tree** (≥500 CCNA / ≥400 ENCOR questions, 20 labs). Windows installer, updater, registry, and CI are implemented; complete the beta matrix in `docs/v020-beta-checklist.md` before publishing a public tag. See `AGENTS.md`, `PRIVACY.md`, and `SUPPORT.md`.

Shipped practice content targets **CCNA 200-301 v1.1** and **CCNP ENCOR 350-401 v1.2**. Objective maps are taken from Cisco’s public exam topics; registry refresh date: **2026-07-31** (`src/openboson/exsim/objectives.py`).

## Architecture

OpenBoson is a single Python desktop application:

- **GUI:** PySide6 (Qt for Python), with a modern dark-first theme.
- **Engine:** Pure Python modules for question-bank parsing, exam sessions, lab grading, and simulation orchestration.
- **Persistence:** SQLite in the user data directory.
- **Content format:** YAML question banks and lab definitions; human-readable, diff-friendly, and local-first.
- **Optional HTTP layer:** FastAPI/uvicorn for headless use and automated testing.

## Quick start

```bash
# Install (editable)
pip install -e ".[all]"

# Run GUI
openboson gui

# Run engine server (optional, for headless use)
openboson serve --port 0
```

## License

MIT. See `LICENSE`.

## Contributing

Contributions are welcome. Please open an issue first to discuss substantial changes. All content shipped with the repository is original demo material; we do not accept copyrighted exam dumps or proprietary question banks.
