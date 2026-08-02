# Privacy

OpenBoson is a **local-first** study application. There is no account system.

## What stays on your computer

- Practice exam history, lab results, and settings are stored under your user data directory (`~/.openboson/` on most systems, or `%USERPROFILE%\.openboson` on Windows).
- Question banks and labs you install as packs live under that same directory.
- Application logs are written to `~/.openboson/logs/openboson.log`.
- SQLite data (`openboson.db`) is owned by you; uninstalling the app does not automatically wipe this folder.

OpenBoson does **not** upload study activity, crash reports, or product telemetry.

## Network access

The only automatic network call in a packaged release is an **optional update check** against GitHub Releases for the configured repository. Development checkouts disable update checks unless release build metadata is present.

Update downloads use HTTPS and are verified with SHA-256 checksums from release metadata. Hosts are limited to GitHub-related endpoints.

You can disable update checks in Settings, or set the environment variable:

```text
OPENBOSON_SKIP_UPDATE=1
```

## Answers and secrets

Correct answers, solution configs, and exam content are never sent over the network by the app. Logs avoid recording correct answers by default.

Demo banks and lab solutions that ship in this open-source repository are intentionally public study material — not a network leak.

## Optional headless server

`openboson serve` starts a local HTTP API for testing/integrations. It has no authentication. Keep it bound to localhost on trusted machines only.

## Contact

See `SUPPORT.md` for diagnostics and `SECURITY.md` for vulnerability reporting.
