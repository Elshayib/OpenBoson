# Windows install verification checklist (v0.2.2+)

Optional community / maintainer verification for packaged Windows builds.
**v0.2.2 is already published** — use this after downloading assets from
[GitHub Releases](https://github.com/Elshayib/OpenBoson/releases/tag/v0.2.2)
or after cutting a new tag.

## Environments

- [ ] Clean Windows 10 install (no Python)
- [ ] Clean Windows 11 install (no Python)
- [ ] Upgrade from a prior v0.2.x install (settings/DB preserved)
- [ ] Offline startup (no network)
- [ ] GitHub outage / bad manifest / bad hash (updater diagnostics only)

## Flows

- [ ] Installer completes per-user under `%LocalAppData%\Programs\OpenBoson`
- [ ] Start menu entry launches GUI
- [ ] Settings/history/user packs survive upgrade
- [ ] Failed/cancelled installer leaves prior app runnable
- [ ] Reinstall previous version retains forward-compatible user data backup
- [ ] Practice check + rationale
- [ ] Blueprint exam finish + stats weak-domain CTA
- [ ] Multi-device lab check/reset/finish

## Performance budgets (reference i5/16GB/SSD)

- [ ] Packaged cold start ≤ 8s
- [ ] Registry refresh @ ~1k questions ≤ 3s
- [ ] Blueprint creation ≤ 500ms
- [ ] Installer ≤ 250MB
- [ ] Idle GUI ≤ 350MB

## Publish gate (when cutting a new tag)

- [ ] CI green on tag commit
- [ ] Assets: `OpenBoson-Setup-X.Y.Z.exe`, `.sha256`, `OpenBoson-X.Y.Z.json`
- [ ] Tag == pyproject version == build info packaged version
- [ ] Release notes mention unsigned installer / SmartScreen
