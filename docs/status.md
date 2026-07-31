# Project status (handoff)

Last synced: **2026-07-31** · Current release: **[v0.2.2 Study Ready](https://github.com/Elshayib/OpenBoson/releases/tag/v0.2.2)**

Use this file (plus `AGENTS.md` and `docs/deferred-releases.md`) when resuming work. The full competitive roadmap lives in the local Cursor plan `openboson_competitive_roadmap_ceb1329f` and must stay out of git.

## Shipped

| Area | Notes |
|------|--------|
| ExSim | Practice library (paginated), blueprints, Check + rationales, keyboard drag-match |
| NetSim | OpenIOS labs, reset, per-device / weighted grading, VLAN-aware L2 |
| Content | Domain shards under `content/questions/`; ≥500 CCNA / ≥400 ENCOR; 20 labs |
| Platform | Registry, stats weak-domains, settings, logging, DB backups, light/dark theme |
| CI | Windows + Ubuntu; ruff; typed-core mypy; content + lab jobs |
| Packaging | PyInstaller onedir + Inno per-user installer; GitHub Releases updater |

## Open / known

- Windows installer is **unsigned** (SmartScreen expected). Signing is a v1.0 item.
- Optional community install matrix: [`v020-beta-checklist.md`](v020-beta-checklist.md) (not a blocker for starting v0.3).
- Full-package `mypy src/openboson` is not green yet; expand typed-core gradually ([`quality-baseline.md`](quality-baseline.md)).

## Next release: v0.3 ExSim depth

Start here — details in [`deferred-releases.md`](deferred-releases.md):

1. Session persistence + pause/resume — **in progress** (engine snapshot, SQLite active sessions, GUI Pause & Exit / Dashboard resume, API pause/resume/list)
2. Custom exam builder (presets)
3. Exports (HTML / JSON / CSV / PDF)
4. Scale content toward ≥1000 CCNA / ≥800 ENCOR
5. Meaningful PBQ / sim coverage

Do **not** begin v0.4 NetSim depth, Designer, or pack ecosystem until v0.3 gates pass.

## Local-only (never commit)

- `.cursor/` (plans, rules)
- `IDEA.md`
- Agent transcripts and private notes

## Quick commands

```bash
pip install -e ".[all]"
pytest -v
openboson gui
make check   # or: pwsh -File scripts/dev.ps1 check
```

Tag a release only when `pyproject.toml` version matches the `v*` tag; `release.yml` builds Windows assets.
