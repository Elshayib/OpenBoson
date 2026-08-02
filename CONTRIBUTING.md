# Contributing

Thanks for helping improve OpenBoson.

## Before you start

1. Open an issue for substantial features or behavior changes.
2. Read `AGENTS.md` for architecture boundaries and `docs/status.md` for current handoff.
3. Keep diffs focused; match existing style (Python 3.11+, ruff line length 100).

## Development setup

```bash
pip install -e ".[all]"
pytest -v
ruff check src/openboson tests scripts
ruff format --check src/openboson tests scripts
openboson gui
```

On Windows you can also use `pwsh -File scripts/dev.ps1 check`.

## Code boundaries

- Engine logic under `src/openboson/` (except `gui/`) must not import PySide6/Qt.
- The GUI talks to the engine through `gui/engine.py`, not direct HTTP in normal use.
- Never leak correct answers in API question payloads (`exsim/router.py`).

## Content rules

- Tag questions and labs with valid CCNA / ENCOR topic codes.
- **Only original demo/community material** — no copyrighted exam dumps or proprietary Boson content.
- PRs that add dump-derived content will be closed.

## Pull requests

- Prefer clear subjects: `Fix …`, `Add …`, `Update …`.
- Include tests for engine changes; use pytest-qt for GUI widget behavior.
- Do not commit `.cursor/`, `IDEA.md`, `.env`, secrets, or local IDE junk.
- Do not push a `v*` release tag until GitHub Actions **CI** is green on that commit.

## Security

See `SECURITY.md` for vulnerability reporting. Do not discuss active exploits in public issues.
