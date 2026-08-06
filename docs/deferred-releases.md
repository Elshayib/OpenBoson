# Later releases (post v0.2.2)

**Current:** v0.4.1 Lab console polish is shipped. **Next primary focus is Labs Quality**
(multi-device scenarios + honest verify), with v0.5 question-pool floors as a **thinner parallel** track.
See [`status.md`](status.md) and [`lab-authoring.md`](lab-authoring.md).

Labs stay **pre-made only** (bundled demo labs). In-app lab creation / Network Designer
and a pack-store product track are **out of scope**.

## v0.3 — ExSim depth (DONE)

Shipped in **v0.3.0**:

- Custom exam builder (presets, seed, filters)
- Pause/resume with SQLite persistence
- Domain trends / heatmap by exam version
- Score/review export (HTML, JSON, CSV, Print-PDF; redacted mode)
- API + GUI parity for finish, mark, coverage, session list/resume, custom exams

## v0.4 — NetSim depth (DONE)

Shipped in **v0.4.0**:

- ≥50 golden labs; catalog filters (objective, difficulty, text)
- Broader OpenIOS matrix (incl. interface jump from config-if/vlan)
- Packet semantics: ARP, route-consistent ping/traceroute, OSPF-derived paths where modeled
- Multi-device grading / reset / replay + `verify.ping` labs
- 10-device lab: ≤100 ms/command on reference hardware
- Correct `base_config` application in privileged config mode

## v0.4.x — Lab UI + Cisco CLI polish (DONE)

Shipped in **v0.4.1**:

- Theme console via QSS; Ctrl+Z, selection/copy, clearer banners
- Lab session chrome polish (objectives, actions, splitter)
- OpenIOS fidelity for shipped labs (show/? completion, STP / EtherChannel / IPv6, paging)
- Read-only topology display polish

## Labs Quality — scenario rewrite (IN PROGRESS / NEXT)

North star: **balanced ladder** — rewrite content on today’s OpenIOS, deepen fidelity only
where behavioral verify would otherwise be fake. Goal: better than Boson on scenario quality.

- Authoring standard + tiers: [`lab-authoring.md`](lab-authoring.md) (`gold` / `drill` / `scale`)
- Catalog audit: [`lab-catalog-audit.md`](lab-catalog-audit.md)
- Floors: ≥20 gold (≥3 devices, ≥3 tasks, verify.ping/show); ≥25 total labs; ≥3 ENCOR gold
- ACL path filtering for ICMP deny/permit verify
- Catalog UI: Scenario / CLI drill / Scale badges + type filter
- Rebuild helper: `python scripts/build_gold_lab_catalog.py`

## v0.5 — Educational Depth & Full Topic Coverage (PARALLEL)

CCNA 200-301 v1.1 + ENCOR 350-401 v1.2 only (no ENARSI).

- Full CCNA / ENCOR leaf coverage (≥12 / ≥15 per topic); pool floors ≥636 / ≥405
- Practice Check: correct / incorrect only (no explanation essays in the app)
- Production polish + pytest / pytest-qt coverage
- Authoring standard: [`content-authoring.md`](content-authoring.md)

Pool volume must not outrank Labs Quality for release prioritization.

## Post-v0.5 / toward v1.0

- Further volume (≥1000 CCNA / ≥800 ENCOR if not already exceeded)
- ≥5% PBQ/sim items with structured grading / OpenIOS where feasible
- ENARSI stays disabled unless a versioned objective map and ≥100 valid questions exist
- Further OpenIOS fidelity (STP/NAT/DHCP traffic effects where gold labs need them)

## v1.0 — Competitive core

- Authenticode + macOS/Linux packages; signed updates
- Documented simulation scope vs real IOS
- Polished UX / a11y / support; objective maps refreshed
- Content gates above must pass before the v1.0 tag
