# Project status (handoff)

Last synced: **2026-08-02** · Current release: **[v0.4.1 Lab console polish](https://github.com/Elshayib/OpenBoson/releases/tag/v0.4.1)**

Use this file (plus `AGENTS.md` and `docs/deferred-releases.md`) when resuming work. Keep local Cursor plans and private notes out of git.

## Shipped

| Area | Notes |
|------|--------|
| ExSim | Practice library, blueprints, custom exams, Check (correct/incorrect), pause/resume, exports |
| NetSim | OpenIOS labs, catalog filters, reset/replay, per-device grading, ARP, OSPF-derived routes, VLAN-aware L2 (**≥50 labs**) |
| Lab UI | Themed console + topology; Ctrl+Z / paging; matrix STP/EtherChannel/IPv6 CLI |
| Content | Domain shards; teaching-depth standard; per-leaf floors toward v0.5 |
| Platform | Registry, stats weak-domains + heatmap, settings, logging, DB backups, light/dark theme |
| CI | Windows + Ubuntu; ruff; typed-core mypy; content + lab jobs |
| Packaging | PyInstaller onedir + Inno per-user installer; GitHub Releases updater |

## Open / known

- Windows installer is **unsigned** (SmartScreen expected). Signing is a v1.0 item.
- Optional community install matrix: [`v020-beta-checklist.md`](v020-beta-checklist.md).
- Full-package `mypy src/openboson` is not green yet; expand typed-core gradually ([`quality-baseline.md`](quality-baseline.md)).
- Labs are **pre-made / bundled only**. No in-app lab creation and no pack-store product track.

## Next release: v0.5 Educational Depth & Full Topic Coverage

Details in [`deferred-releases.md`](deferred-releases.md) and [`content-authoring.md`](content-authoring.md):

1. Full CCNA / ENCOR leaf coverage (≥12 / ≥15 per topic)
2. Practice Check stays correct / incorrect only (no explanation UI)
3. Production polish and tests; then cut **0.5.0** when gates stay green

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
```

Push release commits **without** a tag; wait for GitHub CI green, then tag (`release-tags-ci` rule).
