# OpenBoson

An open-source, fully-local study platform that combines Boson ExSim-style practice exams and Boson NetSim-style guided labs / network simulator for Cisco certifications.

Shipped practice content targets **CCNA 200-301 v1.1** and **CCNP ENCOR 350-401 v1.2**. Objective maps are taken from Cisco’s public exam topics (Learning Network / topics PDFs); registry refresh date: **2026-07-31** (see `src/openboson/exsim/objectives.py`).

## Status

**[v0.4.1 Lab console polish](https://github.com/Elshayib/OpenBoson/releases/tag/v0.4.1)** — themed Cisco terminal, Ctrl+Z/paging, OpenIOS matrix cmds. Next major track is **v0.5** (full CCNA/ENCOR topic coverage).




### At a glance

- **Local-first** — study data stays on your machine (`PRIVACY.md`); no accounts, no study telemetry
- **Windows installer** — unsigned until v1.0 (SmartScreen expected; `SUPPORT.md`)
- **Original demo content only** — no copyrighted exam dumps accepted

- Download: [GitHub Releases](https://github.com/Elshayib/OpenBoson/releases)
- Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md) · Conduct: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- Security: [`SECURITY.md`](SECURITY.md) · Privacy: [`PRIVACY.md`](PRIVACY.md) · Support: [`SUPPORT.md`](SUPPORT.md)
- Developer handoff: `docs/status.md` · Agent guide: `AGENTS.md`

## Architecture

OpenBoson is a single Python desktop application:

- **GUI:** PySide6 (Qt for Python), with a modern dark-first theme.
- **Engine:** Pure Python modules for question-bank parsing, exam sessions, lab grading, and simulation orchestration.
- **Persistence:** SQLite in the user data directory.
- **Content format:** YAML question banks and lab definitions; human-readable, diff-friendly, and local-first.
- **Optional HTTP layer:** FastAPI/uvicorn for headless use and automated testing (localhost; no auth).

## Quick start

```bash
# Install (editable)
pip install -e ".[all]"

# Run GUI
openboson gui

# Run engine server (optional, for headless use — keep on localhost)
openboson serve --port 0
```

## License

MIT. See `LICENSE`.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Please open an issue before substantial changes. All content shipped with the repository is original demo material; we do not accept copyrighted exam dumps or proprietary question banks.
