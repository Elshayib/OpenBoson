# Project status (handoff)

Last synced: **2026-08-02** · Current release: **[v0.4.0 NetSim Depth](https://github.com/Elshayib/OpenBoson/releases/tag/v0.4.0)**

Use this file (plus `AGENTS.md` and `docs/deferred-releases.md`) when resuming work. The full competitive roadmap lives in the local Cursor plan `openboson_competitive_roadmap_ceb1329f` and must stay out of git.

## Shipped

| Area | Notes |
|------|--------|
| ExSim | Practice library, blueprints, custom exams, Check + rationales, pause/resume, exports |
| NetSim | OpenIOS labs, catalog filters, reset/replay, per-device grading, ARP, OSPF-derived routes, VLAN-aware L2 (**≥50 labs**) |
| Content | Domain shards; ≥500 CCNA / ≥400 ENCOR; ≥50 labs |
| Platform | Registry, stats weak-domains + heatmap, settings, logging, DB backups, light/dark theme |
| CI | Windows + Ubuntu; ruff; typed-core mypy; content + lab jobs |
| Packaging | PyInstaller onedir + Inno per-user installer; GitHub Releases updater |

## Open / known

- Windows installer is **unsigned** (SmartScreen expected). Signing is a v1.0 item.
- Optional community install matrix: [`v020-beta-checklist.md`](v020-beta-checklist.md).
- Full-package `mypy src/openboson` is not green yet; expand typed-core gradually ([`quality-baseline.md`](quality-baseline.md)).
- Question-bank scale (≥1000/800) and ≥5% PBQ are deferred to a **pre-v1.0 content gate** (after v0.6).

## Next: v0.4.x lab UI + Cisco CLI polish

Landing on `master` — Designer (v0.5) waits until this cut is tagged:

1. Theme `CiscoTerminal` via QSS; Ctrl+Z, selection/copy, tab focus — **done**
2. Lab session chrome (actions, objectives, splitter) — **done**
3. OpenIOS fidelity: banner, show/? completion, STP/EtherChannel/IPv6, paging — **done**
4. Read-only topology display polish (layout, theme, fit-to-view) — **done**

Tag a `v0.4.x` only after GitHub CI is green on the polish commit.

## After polish: v0.5 Network Designer

Details in [`deferred-releases.md`](deferred-releases.md):

1. Freeze lab schema v2
2. Editable topology canvas; save/load user topologies
3. Round-trip through `LabWorld`; pytest-qt for invalid links and save/load

Do **not** begin v0.6 packs until v0.5 Designer gates pass.

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

Push release commits **without** a tag; wait for GitHub CI green, then tag (`release-tags-ci` rule).
