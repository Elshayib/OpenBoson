# Quality baseline (v0.2)

OpenBoson enables Ruff and MyPy in CI on **governed paths**. Historical debt outside those paths is tracked here; do not add new violations or weaken rules to clear the baseline.

## Governed today

- `ruff check` / `ruff format --check`: `src/openboson`, `tests`, `scripts`
- `mypy`: typed-core modules listed in `Makefile` / `.github/workflows/ci.yml`
- `pytest`: full suite on Windows and Ubuntu (Qt offscreen)

## Known debt (grow-down over time)

- Full-package `mypy src/openboson` is not yet green; expand the typed-core list module-by-module.
- Packaging scripts (`openboson.spec`, Inno) land in v0.2.0 installer work; treat generated `_build_info.py` as CI-owned at release time.
- Content volume/quality gates tighten in v0.2.1 / v0.2.2 (counts, rationale uniqueness, lab golden solutions).

## Local commands

```bash
make check
# or
pwsh -File scripts/dev.ps1 check
```
