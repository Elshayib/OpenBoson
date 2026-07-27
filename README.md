# OpenBoson

An open-source, fully-local study platform that combines Boson ExSim-style practice exams and Boson NetSim-style guided labs / network simulator, focused first on Cisco CCNA 200-301 topics.

## Status

Early development. See `.hermes/plans/2026-07-27_OpenBoson_ExSim_NetSim_v1.md` for the full implementation plan.

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
pip install -e .

# Run GUI
openboson gui

# Run engine server (optional, for headless use)
openboson serve --port 0
```

## License

MIT. See `LICENSE`.

## Contributing

Contributions are welcome. Please open an issue first to discuss substantial changes. All content shipped with the repository is original demo material; we do not accept copyrighted exam dumps or proprietary question banks.
