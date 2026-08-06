# Project status (handoff)

Last synced: **2026-08-06** · Current release: **[v0.4.1 Lab console polish](https://github.com/Elshayib/OpenBoson/releases/tag/v0.4.1)**

Use this file (plus `AGENTS.md` and `docs/deferred-releases.md`) when resuming work. Keep local Cursor plans and private notes out of git.

## Shipped

| Area | Notes |
|------|-------|
| ExSim | Practice library, blueprints, custom exams, Check (correct/incorrect), pause/resume, exports |
| NetSim | OpenIOS labs, catalog filters + Scenario/Drill badges, reset/replay, per-device grading, ARP, OSPF-derived routes, VLAN-aware L2, **ACL path filtering** |
| Lab catalog | Labs Quality rewrite: **≥20 gold** multi-device scenarios + drills/scale; ENCOR gold wave (≥3); see `docs/lab-authoring.md` |
| Lab UI | Soft Daylight modern tooling; IDE console; verify coaching hints |
| Content | Domain shards; teaching-depth standard; per-leaf floors toward v0.5 |
| Platform | Registry, stats weak-domains + heatmap, settings, logging, DB backups, light/dark theme |
| CI | Windows + Ubuntu; ruff; typed-core mypy; content + lab quality jobs |
| Packaging | PyInstaller onedir + Inno per-user installer; GitHub Releases updater |

## Open / known

- Windows installer is **unsigned** (SmartScreen expected). Signing is a v1.0 item.
- Optional community install matrix: [`v020-beta-checklist.md`](v020-beta-checklist.md).
- Full-package `mypy src/openboson` is not green yet; expand typed-core gradually ([`quality-baseline.md`](quality-baseline.md)).
- Labs are **pre-made / bundled only**. No in-app lab creation and no pack-store product track.
- OpenIOS fidelity is **simplified** vs real IOS (documented in [`openios-command-matrix.md`](openios-command-matrix.md)).

## Next focus: Labs Quality (primary) + v0.5 pool floors (parallel)

1. **Primary:** expand/harden gold scenarios; deepen fidelity only where verify needs it (ACL shipped; STP/NAT packet effects still limited).
2. **Parallel (thinner):** CCNA / ENCOR question-pool leaf coverage (`docs/content-authoring.md`) — do not outrank believable NetSim.
3. Practice Check stays correct / incorrect only (no explanation UI).

Details: [`deferred-releases.md`](deferred-releases.md), [`lab-authoring.md`](lab-authoring.md), [`lab-catalog-audit.md`](lab-catalog-audit.md).

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
python scripts/assemble_question_pools.py
python scripts/build_gold_lab_catalog.py   # rebuild demo_labs from gold builder
```

Push release commits **without** a tag; wait for GitHub CI green, then tag (`release-tags-ci` rule).
