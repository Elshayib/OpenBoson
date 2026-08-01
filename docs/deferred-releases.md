# Later releases (post v0.2.2)

**Current:** v0.3.0 ExSim Depth is shipped. Next executable track is **v0.4 NetSim depth**.
See [`status.md`](status.md) for handoff.

Question-bank content scale (≥1000 CCNA / ≥800 ENCOR) and ≥5% PBQ/sim depth are
**deferred until just before v1.0** — after packs (v0.6), as a pre-1.0 content gate.
Do not block NetSim / Designer / packs on that work.

## v0.3 — ExSim depth (DONE)

Shipped in **v0.3.0**:

- Custom exam builder (presets, seed, filters)
- Pause/resume with SQLite persistence
- Domain trends / heatmap by exam version
- Score/review export (HTML, JSON, CSV, Print-PDF; redacted mode)
- API + GUI parity for finish, mark, coverage, session list/resume, custom exams

## v0.4 — NetSim depth (NEXT)

- ≥50 golden labs; catalog filters (objective, difficulty, text)
- Broader OpenIOS matrix required by those labs
- Expanded packet semantics (ARP, route-consistent ping/traceroute, OSPF-derived paths where modeled)
- Mature multi-device grading / reset / replay
- 10-device lab: ≤100 ms/command on reference hardware

Suggested order: catalog filters → lab scale toward 50 → grading/verify maturity → packet semantics → replay → perf lab → tag `v0.4.0`.

## v0.5 — Network Designer

- Freeze lab schema v2 first
- Editable topology canvas; save/load user topologies
- Round-trip through `LabWorld`; pytest-qt for invalid links and save/load

## v0.6 — Pack ecosystem

- Curated GitHub pack index, verified manifests, install/update/remove UI
- No executable pack content; DMCA / content report process

## Pre-v1.0 content gate

- ≥1,000 CCNA and ≥800 ENCOR questions
- ≥5% PBQ/sim items with structured grading / OpenIOS where feasible
- ENARSI stays disabled unless a versioned objective map and ≥100 valid questions exist

## v1.0 — Competitive core

- Authenticode + macOS/Linux packages; signed updates
- Documented simulation scope vs real IOS
- Polished UX / a11y / support; objective maps refreshed
- Content gate above must pass before the v1.0 tag
