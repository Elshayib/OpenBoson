"""Release/build metadata injected by CI for packaged builds.

Development checkouts leave ``GITHUB_REPOSITORY`` unset; the updater falls back
to the public OpenBoson repository identity unless ``OPENBOSON_SKIP_UPDATE=1``.
"""

from __future__ import annotations

GITHUB_REPOSITORY: str | None = None
CHANNEL: str = "dev"
COMMIT: str | None = None
BUILD_TIME: str | None = None
PACKAGED_VERSION: str | None = None


def update_checks_enabled() -> bool:
    """Return True only when a release build stamped a GitHub repository identity."""
    return bool(GITHUB_REPOSITORY)
