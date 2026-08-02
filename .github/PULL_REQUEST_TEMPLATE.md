name: Pull Request

## Summary

<!-- What changed and why (user-facing outcome preferred). -->

-

## Test plan

- [ ] `pytest -v` (or scoped suites for the touched area)
- [ ] `ruff check` / `ruff format --check` on governed paths
- [ ] Manual GUI smoke if UI changed (`openboson gui`)

## Checklist

- [ ] No secrets, `.env`, `.cursor/`, or private notes
- [ ] No copyrighted exam dumps / proprietary content
- [ ] Engine modules still free of Qt imports (unless change is under `gui/`)
