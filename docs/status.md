# Project status (handoff)

Last synced: **2026-08-01** · Current release: **[v0.3.0 ExSim Depth](https://github.com/Elshayib/OpenBoson/releases/tag/v0.3.0)**

Use this file (plus `AGENTS.md` and `docs/deferred-releases.md`) when resuming work. The full competitive roadmap lives in the local Cursor plan `openboson_competitive_roadmap_ceb1329f` and must stay out of git.

## Shipped

| Area | Notes |
|------|--------|
| ExSim | Practice library, blueprints, custom exams, Check + rationales, pause/resume, exports |
| NetSim | OpenIOS labs, reset, per-device / weighted grading, VLAN-aware L2 |
| Content | Domain shards; ≥500 CCNA / ≥400 ENCOR; 20 labs (v0.3.x content scale still open) |
| Platform | Registry, stats weak-domains + heatmap, settings, logging, DB backups, light/dark theme |
| CI | Windows + Ubuntu; ruff; typed-core mypy; content + lab jobs |
| Packaging | PyInstaller onedir + Inno per-user installer; GitHub Releases updater |

## Open / known

- Windows installer is **unsigned** (SmartScreen expected). Signing is a v1.0 item.
- Optional community install matrix: [`v020-beta-checklist.md`](v020-beta-checklist.md).
- Full-package `mypy src/openboson` is not green yet; expand typed-core gradually ([`quality-baseline.md`](quality-baseline.md)).
- **Content follow-up (post-0.3.0):** scale toward ≥1000 CCNA / ≥800 ENCOR and ≥5% PBQ/sim with structured grading.

## v0.3 product gates

1. Session persistence + pause/resume — **done**
2. Custom exam builder (presets) — **done**
3. Exports (HTML / JSON / CSV / Print-PDF, redacted) — **done**
4. Domain trends / heatmap by exam version — **done**
5. API + GUI parity (coverage, custom exams, session list/resume) — **done**
6. Content ≥1000/800 + ≥5% PBQ — **deferred** to v0.3.x content track

Do **not** begin v0.4 NetSim depth, Designer, or pack ecosystem until you intentionally start that track.

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
