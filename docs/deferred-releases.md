# Later releases (post v0.2.2)

**Current:** v0.2.2 Study Ready is shipped. See [`status.md`](status.md) for handoff.

Execute **v0.3 next**. Do not start later tracks until that release’s gates pass.

## v0.3 — ExSim depth (NEXT)

Acceptance targets:

- Custom exam builder: cert / topic / difficulty / missed / unseen / length / time; saved JSON presets; deterministic seed
- Pause/resume: answers, order, index, bookmarks, marked items, remaining time; timer frozen while paused; survives restart
- Domain breakdown persistence; trends / heatmaps by exam version
- Export score/review: HTML, JSON, CSV, print-to-PDF; redacted mode must not leak answers
- ≥1,000 CCNA and ≥800 ENCOR questions; ≥5% PBQ/sim items with structured grading / OpenIOS where feasible
- ENARSI stays disabled unless a versioned objective map and ≥100 valid questions exist
- API + GUI parity for finish, mark-for-review, coverage, session list/resume

Suggested order: persistence → custom builder → exports → content scale → PBQs → tag `v0.3.0`.

## v0.4 — NetSim depth

- ≥50 golden labs; catalog filters (objective, difficulty, text)
- Broader OpenIOS matrix required by those labs
- Expanded packet semantics (ARP, route-consistent ping/traceroute, OSPF-derived paths where modeled)
- Mature multi-device grading / reset / replay
- 10-device lab: ≤100 ms/command on reference hardware

## v0.5 — Network Designer

- Freeze lab schema v2 first
- Editable topology canvas; save/load user topologies
- Round-trip through `LabWorld`; pytest-qt for invalid links and save/load

## v0.6 — Pack ecosystem

- Curated GitHub pack index, verified manifests, install/update/remove UI
- No executable pack content; DMCA / content report process

## v1.0 — Competitive core

- Authenticode + macOS/Linux packages; signed updates
- Documented simulation scope vs real IOS
- Polished UX / a11y / support; objective maps refreshed
