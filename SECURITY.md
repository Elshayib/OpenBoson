# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.4.x   | Yes |
| Older   | Best-effort only |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security-sensitive reports.

1. Use GitHub’s [private vulnerability reporting](https://github.com/Elshayib/OpenBoson/security/advisories/new) for this repository, **or**
2. Email the maintainers via the contact listed on the GitHub profile / org for this project.

Include:

- OpenBoson version and install type (installer vs `pip install`)
- OS version
- Clear reproduction steps
- Impact assessment (local data exposure, supply-chain, RCE, etc.)

We aim to acknowledge reports within a few days and to ship fixes before any public disclosure when feasible.

## Threat model (what this app is)

OpenBoson is a **local-first desktop study app**:

- Study data stays under `~/.openboson/` (see `PRIVACY.md`).
- There is **no user account** and **no study telemetry**.
- Packaged builds may perform an **optional HTTPS update check** against GitHub Releases (disable in Settings or with `OPENBOSON_SKIP_UPDATE=1`).
- Downloads are verified with SHA-256 (and size) against release metadata; update URLs are restricted to GitHub hosts.

## Known product caveats

- Windows installers are **unsigned** until Authenticode work (planned for v1.0). Prefer official GitHub Releases downloads; expect SmartScreen warnings (see `SUPPORT.md`).
- `openboson serve` is an optional local FastAPI layer for headless/testing. It has **no authentication**. Bind only to localhost on trusted machines; do not expose it on untrusted networks.
- Demo question banks and lab solution configs are intentionally public (open study content). Do not file “answer key leaked” reports against shipped demo YAML.

## Secrets and private files

Never commit `.env`, credentials, private keys, `.cursor/`, `IDEA.md`, or local agent notes. See `.gitignore` and `CONTRIBUTING.md`.
