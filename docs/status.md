# Project status (handoff)

Last synced: **2026-08-01** · Current release: **[v0.3.0 ExSim Depth](https://github.com/Elshayib/OpenBoson/releases/tag/v0.3.0)**

Use this file (plus `AGENTS.md` and `docs/deferred-releases.md`) when resuming work. The full competitive roadmap lives in the local Cursor plan `openboson_competitive_roadmap_ceb1329f` and must stay out of git.

## Shipped

| Area | Notes |
|------|--------|
| ExSim | Practice library, blueprints, custom exams, Check + rationales, pause/resume, exports |
| NetSim | OpenIOS labs, reset, per-device / weighted grading, VLAN-aware L2 (20 labs) |
| Content | Domain shards; ≥500 CCNA / ≥400 ENCOR; 20 labs |
| Platform | Registry, stats weak-domains + heatmap, settings, logging, DB backups, light/dark theme |
| CI | Windows + Ubuntu; ruff; typed-core mypy; content + lab jobs |
| Packaging | PyInstaller onedir + Inno per-user installer; GitHub Releases updater |

## Open / known

- Windows installer is **unsigned** (SmartScreen expected). Signing is a v1.0 item.
- Optional community install matrix: [`v020-beta-checklist.md`](v020-beta-checklist.md).
- Full-package `mypy src/openboson` is not green yet; expand typed-core gradually ([`quality-baseline.md`](quality-baseline.md)).
- Question-bank scale (≥1000/800) and ≥5% PBQ are deferred to a **pre-v1.0 content gate** (after v0.6).

## Next release: v0.4 NetSim depth

Start here — details in [`deferred-releases.md`](deferred-releases.md):

1. Lab catalog filters (objective / difficulty / text) — **next**
2. Scale toward ≥50 golden labs
3. Grading maturity (verify.ping, consistent per-device rules)
4. Packet semantics (ARP, route-consistent ping/traceroute, OSPF paths where modeled)
5. Command replay after reset
6. 10-device lab perf gate (≤100 ms/command)

Do **not** begin v0.5 Designer or v0.6 packs until v0.4 gates pass.

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
