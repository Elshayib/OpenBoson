# Support

## Quick diagnostics

| Item | Location |
|------|----------|
| User data | `~/.openboson/` (Windows: `%USERPROFILE%\.openboson`) |
| Database | `openboson.db` |
| Settings | `settings.json` |
| Logs | `logs/openboson.log` |
| Backups | `backups/openboson-*.db` |
| User packs | `packs/` |
| Loose banks/labs | `banks/`, `labs/` |

In the app: **Settings → Open data folder / Open logs / Open backups**.

## Database backups

Before schema migrations on an existing database, OpenBoson copies `openboson.db` into `backups/` and keeps the newest five files.

To restore a backup manually:

1. Quit OpenBoson.
2. Copy a backup over `openboson.db` (keep an extra copy first).
3. Restart the app.

## Reset options

- **Reset cache** (Settings): clears `~/.openboson/cache` only.
- **Full database reset**: quit the app, delete or rename `openboson.db`, then restart. Study history will be empty. Prefer restoring a backup when possible.

## Windows SmartScreen / unsigned installs

Early Windows installers may be **unsigned**. Windows Defender SmartScreen can warn on first run. Prefer downloads from the official GitHub Releases page for this repository. Authenticode signing is planned before v1.0.

## Updates

- Stable is the default channel; beta is opt-in in Settings.
- Updates replace application files only; they never overwrite `~/.openboson/` user data.
- If an update fails or is cancelled, the previously installed app should remain runnable.
- Set `OPENBOSON_SKIP_UPDATE=1` to disable checks entirely.

## Content problems

Use Settings content diagnostics (when available) or check logs after **Refresh**. Bundled content wins over user packs on ID collisions; colliding packs are rejected as a unit.

## Reporting issues

Open a GitHub issue with:

- OpenBoson version
- OS version
- Steps to reproduce
- Relevant log snippets (remove any personal paths you do not want to share)
