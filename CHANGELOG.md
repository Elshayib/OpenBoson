# Changelog

All notable changes to OpenBoson are documented in this file.

## [0.4.1] — 2026-08-02 — Lab console polish

### Application
- Theme `CiscoTerminal` and topology canvas for light/dark via QSS.
- Terminal muscle memory: Ctrl+Z → `end`, Ctrl+L clear, history selection/copy, `--More--` paging keys.
- Lab session chrome: objective styles, Lab actions menu, console-focused splitter, tab focus.
- OpenIOS: IOS-shaped connect banner, richer `show`/`interface` completion, `terminal length` paging.
- Matrix commands typed live: `spanning-tree portfast`, `channel-group … mode …`, `ipv6 unicast-routing` / `ipv6 address`.
- Topology display: honor `Device.x`/`y`, role-banded layout, fit-to-view, zoom toward cursor.

### Docs
- Handoff points at this polish cut; Network Designer remains the next major track (v0.5).

### Known Issues
- Windows installers remain unsigned until v1.0 Authenticode work (SmartScreen warnings expected).

## [0.4.0] — 2026-08-01 — NetSim Depth

### Application
- Lab catalog filters (objective / difficulty / text) in GUI and `GET /api/v1/labs`.
- Reset & Replay: rebuild lab world and re-feed the session command log (engine, API, GUI).
- OpenIOS: interface jumps from config-if/vlan mode; `base_config` applied under `enable` / `configure terminal`.
- Packet semantics: ARP learning + `show ip arp`; static and simplified OSPF-derived routes for ping/traceroute; `show ip route` shows C/S/O.

### Content
- ≥50 CCNA demo labs (scale campus 10-device lab, generated variants, OSPF two-router reachability).
- Broader `verify.ping` coverage (branch office, dual-router static, VLAN isolation, OSPF).

### Known Issues
- Windows installers remain unsigned until v1.0 Authenticode work (SmartScreen warnings expected).

### Docs
- Handoff synced in `docs/status.md`; next track is Network Designer (v0.5) in `docs/deferred-releases.md`.

## [0.3.0] — 2026-08-01 — ExSim Depth

### Application
- Pause/resume exams with SQLite persistence (answers, order, bookmarks, marks, remaining time); periodic and quit flush.
- Custom exam builder: cert / topic / difficulty / missed / unseen / length / time / seed; JSON presets under `~/.openboson/custom_exams/`.
- Score/review export: HTML, JSON, CSV, and Print/PDF with redacted mode that omits answers and explanations.
- Stats domain × exam-version heatmap and domain trend series; cert/version filters.
- API parity: blueprint coverage, custom-exam presets/preview/sessions, existing pause/resume/list/finish/mark.

### Content
- Pool volume gates remain ≥500 CCNA / ≥400 ENCOR for this release.
- Scaling to ≥1000/800 and ≥5% PBQ/sim depth is deferred to a v0.3.x content track (see `docs/deferred-releases.md`).

### Known Issues
- Windows installers remain unsigned until v1.0 Authenticode work (SmartScreen warnings expected).

### Docs
- Handoff synced in `docs/status.md`; content/PBQ follow-ups documented in `docs/deferred-releases.md`.

## [0.2.2] — 2026-07-31 — Study Ready

### Application
- Usable light theme stylesheet; Settings theme toggle is truthful.
- Content volume gates enforced in tests (≥500 CCNA / ≥400 ENCOR, ≥15% non-SC, ≥20 labs).
- Practice library pagination; keyboard alternatives for drag-match items.

### Content
- Domain-sharded authoring under `content/questions/` with assemble/bootstrap scripts.
- 20 graded CCNA demo labs covering VLAN/trunk/STP/EtherChannel/static/OSPF/ACL/NAT/DHCP/SSH/IPv6.

### Known Issues
- Windows installers remain unsigned until v1.0 Authenticode work (SmartScreen warnings expected).
- Manual Win10/11 install matrix remains optional community verification (`docs/v020-beta-checklist.md`).

### Docs
- Handoff synced in `docs/status.md`; next track documented in `docs/deferred-releases.md` (v0.3).

## [0.2.0] — Platform

### Application
- Version single-sourced from package metadata (`0.2.0`).
- Frozen-safe `resource_paths` for bundled banks/labs and GUI styles.
- Typed settings store with atomic JSON writes.
- Rotating logs and pre-migration SQLite backups.
- Hot-load content registry (bundled / local / packs) with Refresh UI and API.
- Stats weak-domain analytics and Dashboard/Practice deep links.
- GitHub Releases updater (stable/beta) with SHA-256 verification.
- PyInstaller onedir + Inno Setup per-user installer + release workflow.
- CI on Windows/Ubuntu, Makefile / `scripts/dev.ps1`, quality baseline docs.

### OpenIOS / NetSim
- Per-device grading hooks, weighted scoring, verify blocks, lab reset, VLAN-aware L2 checks.

### Migration
- Existing databases are backed up before applying pending schema migrations.
- Answer rows persist topic/cert/exam version identity.

### Known Issues
- See [0.2.2] for current packaging / verification notes.
