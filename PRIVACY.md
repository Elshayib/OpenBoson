# Privacy

OpenBoson is a **local-first** study application.

## What stays on your computer

- Practice exam history, lab results, and settings are stored under your user data directory (`~/.openboson/` on most systems, or `%USERPROFILE%\.openboson` on Windows).
- Question banks and labs you install as packs live under that same directory.
- Application logs are written to `~/.openboson/logs/openboson.log`.

OpenBoson does **not** upload study activity, crash reports, or telemetry in v0.2.

## Network access

The only automatic network call in a packaged release is an **optional update check** against GitHub Releases for the configured repository. Development checkouts disable update checks unless release build metadata is present.

You can disable update checks in Settings, or set the environment variable:

```text
OPENBOSON_SKIP_UPDATE=1
```

## Answers and secrets

Correct answers, solution configs, and full exam dumps are never sent over the network. Logs avoid recording correct answers by default.

## Contact

See `SUPPORT.md` for diagnostics, backup restore, and how to report issues.
