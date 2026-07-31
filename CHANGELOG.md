# Changelog

All notable changes to OpenBoson are documented in this file.

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
- Manual Win10/11 install matrix remains a community verification checklist (`docs/v020-beta-checklist.md`).

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
