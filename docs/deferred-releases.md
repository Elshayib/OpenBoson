# Later releases (post v0.2.2)

**Current:** v0.4.1 is the last tagged release. **Beat Boson core is on `master`**
(teach UI, honest NAT/DHCP/PortFast/EtherChannel, gold fail-before/pass-after,
study loop, first-run, OpenIOS-vs-IOS). See
[`status.md`](status.md) and
[`superpowers/plans/2026-09-04-beat-boson.md`](superpowers/plans/2026-09-04-beat-boson.md).

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

## Labs Quality — scenario rewrite (DONE on master)

North star: **balanced ladder** — rewrite content on today’s OpenIOS, deepen fidelity only
where behavioral verify would otherwise be fake.

- Authoring standard + tiers: [`lab-authoring.md`](lab-authoring.md) (`gold` / `drill` / `scale`)
- Floors: ≥20 gold, ≥25 total, ≥3 ENCOR gold — **met**
- ACL, NAT PAT, DHCP lease, PortFast, EtherChannel change `LabWorld.ping`
- Gold labs for NAT/DHCP/STP/EC fail-before / pass-after (`tests/netsim/test_gold_*_lab.py`)
- Catalog UI: Scenario / CLI drill / Scale badges + type filter
- Rebuild helper: `python scripts/build_gold_lab_catalog.py`

Further gold tickets only where a new feature would otherwise grade on `require:` alone.

## Beat Boson / v0.5 educational depth (DONE on master; unreleased)

CCNA 200-301 v1.1 + ENCOR 350-401 v1.2 only (no ENARSI).

- Per-leaf coverage (≥12 / ≥15); pool floors ≥636 / ≥405
- Practice Check + exam review: explanations and why-wrong (exam mode silent)
- Template distractor phrases banned in CI; 24 CCNA flagship items
- `suggest_next()` study loop; first-run cert picker
- [`openios-vs-ios.md`](openios-vs-ios.md)

Typical pool items can still be thinner than Boson ExSim essays. Do not market
“better explanations than Boson.”

## Post-v0.5 / toward v1.0 (NEXT)

- ≥5% PBQ/sim items with structured grading / OpenIOS — [`superpowers/plans/2026-09-03-pbq-sim-items.md`](superpowers/plans/2026-09-03-pbq-sim-items.md)
- Raise typical-item explanation quality (no new generator stamps)
- Typed-core mypy expansion — [`superpowers/plans/2026-09-03-v1-platform.md`](superpowers/plans/2026-09-03-v1-platform.md)
- Further volume (≥1000 CCNA / ≥800 ENCOR) only after quality
- ENARSI stays disabled unless a versioned objective map and ≥100 valid questions exist

## v1.0 — Competitive core

- Authenticode + macOS/Linux packages; signed updates
- Polished UX / a11y / support; objective maps refreshed
- Content gates above must pass before the v1.0 tag
