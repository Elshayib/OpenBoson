# Quality baseline (v0.2.2+)

OpenBoson enables Ruff and MyPy in CI on **governed paths**. Historical debt outside those paths is tracked here; do not add new violations or weaken rules to clear the baseline.

## Governed today

- `ruff check` / `ruff format --check`: `src/openboson`, `tests`, `scripts`
- `mypy`: typed-core modules listed in `Makefile` / `.github/workflows/ci.yml`
- `pytest`: full suite on Windows and Ubuntu (`QT_QPA_PLATFORM=offscreen`)
- Content/lab jobs: pool volume + quality gates; lab schema/golden checks (Ubuntu jobs install Qt libs)

## Known debt (grow-down over time)

- Full-package `mypy src/openboson` is not yet green; expand the typed-core list module-by-module.
- Generated `_build_info.py` is rewritten at packaging time; keep the repo stub safe for development (update checks disabled without repository identity).
- Content scale for v0.3 (≥1000/800, PBQs) must keep rationale uniqueness and objective validators green.

## Local commands

```bash
make check
# or
pwsh -File scripts/dev.ps1 check
```
