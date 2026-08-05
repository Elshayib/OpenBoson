"""Release/build metadata injected by CI for packaged builds.

Development checkouts leave ``GITHUB_REPOSITORY`` unset. The updater may still
resolve a default public repository for *manual* Settings checks, but automatic
startup update probes require a stamped repository identity (or
``OPENBOSON_SKIP_UPDATE=1`` disables all checks).
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
