# Project status (handoff)

Last synced: **2026-09-04** · Current release: **[v0.4.1 Lab console polish](https://github.com/Elshayib/OpenBoson/releases/tag/v0.4.1)** · Tip: **`master` @ `6228c39`** (CI green)

**Beat Boson core is on `master`.** Plans: [`superpowers/plans/2026-09-04-beat-boson.md`](superpowers/plans/2026-09-04-beat-boson.md). Bar: [`superpowers/specs/2026-09-04-beat-boson-bar.md`](superpowers/specs/2026-09-04-beat-boson-bar.md). OpenIOS scope: [`openios-vs-ios.md`](openios-vs-ios.md).

Use this file (plus `AGENTS.md` and `docs/deferred-releases.md`) when resuming work. Keep local Cursor plans and private notes out of git.

## Shipped

| Area | Notes |
|------|-------|
| ExSim | Practice library, blueprints, custom exams, Check **+ explanations / why-wrong**, pause/resume, exports (redacted still omit teaching) |
| NetSim | OpenIOS labs, catalog filters + Scenario/Drill badges, reset/replay, per-device grading, ARP, OSPF-derived routes, VLAN-aware L2, ACL path filtering |
| Honest ping | NAT PAT, DHCP `ipconfig /renew`, PortFast, EtherChannel bundle vs unbundled STP — see `test_nat_path.py` / `test_dhcp_path.py` / `test_stp_path.py` |
| Lab catalog | ≥20 gold + drills/scale; ENCOR gold ≥3; NAT/DHCP/STP/EC gold labs fail-before / pass-after (`test_gold_*_lab.py`) |
| Lab UI | Soft Daylight modern tooling; IDE console; verify coaching hints |
| Study loop | `suggest_next()` — weak domain → practice or matching gold lab (Home + Stats) |
| Presence | First-run CCNA/ENCOR picker; denser dark/light QSS |
| Content | Domain shards; per-leaf floors; template-phrase CI ban; 24 CCNA flagship items (`content/questions/ccna/FLAGSHIP.md`) |
| Platform | Registry, stats heatmap, settings, logging, DB backups, light/dark theme |
| CI | Windows + Ubuntu; ruff; typed-core mypy; content + lab quality jobs |
| Packaging | PyInstaller onedir + Inno per-user installer; GitHub Releases updater |

## Open / known

- Windows installer is **unsigned** (SmartScreen expected). Signing is a v1.0 item.
- Typical pool items can still be thinner than Boson ExSim essays; do not market “better explanations than Boson.” Flagships + Check UI teach; `ccna-v05-*` stems can stay factory-generic.
- Presence still uses some inline styles (exam grid, heatmap). Hub screens can show more than one primary CTA.
- Optional community install matrix: [`v020-beta-checklist.md`](v020-beta-checklist.md).
- Full-package `mypy src/openboson` is not green yet; expand typed-core gradually ([`quality-baseline.md`](quality-baseline.md)).
- Labs are **pre-made / bundled only**. No in-app lab creation and no pack-store product track.
- OpenIOS fidelity is **simplified** vs real IOS ([`openios-vs-ios.md`](openios-vs-ios.md), [`openios-command-matrix.md`](openios-command-matrix.md)).

## Next focus

1. **PBQ / sim items** — `2026-09-03-pbq-sim-items.md` (≥5% graded via OpenIOS when content exists).
2. **Explanation depth** — keep banning new formula stamps; raise typical-item quality without generator wrappers.
3. **v1 platform leftover** — typed-core mypy expansion (`2026-09-03-v1-platform.md` Task 2+). First-run and `openios-vs-ios.md` already shipped.
4. More gold tickets only where verify would otherwise be fake. No Network Designer.

Details: [`deferred-releases.md`](deferred-releases.md), [`lab-authoring.md`](lab-authoring.md).

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
