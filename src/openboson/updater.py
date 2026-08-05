"""GitHub Releases update checker (stdlib only — no Qt).

Release asset contract (per version ``X.Y.Z`` / ``X.Y.Z-beta.N``):

- installer: ``OpenBoson-Setup-{version}.exe``
- checksum:  ``OpenBoson-Setup-{version}.exe.sha256``
  (lowercase 64-hex SHA-256, two spaces, exact filename)
- manifest:  ``OpenBoson-{version}.json``
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from openboson import __version__ as _app_version
from openboson import _build_info
from openboson.config import settings
from openboson.settings_store import UpdateChannel, load_settings, update_settings

logger = logging.getLogger(__name__)

# Fallback when CI did not stamp ``_build_info`` (pip / editable / older installers).
DEFAULT_GITHUB_REPOSITORY = "Elshayib/OpenBoson"

# Protocol version advertised by this updater implementation (manifest gate).
UPDATER_VERSION = "1.0.0"

METADATA_TIMEOUT_S = 5.0
DOWNLOAD_TIMEOUT_S = 120.0
CHECK_THROTTLE_HOURS = 24
USER_AGENT = f"OpenBoson-Updater/{UPDATER_VERSION} ({_app_version})"

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>beta\.(?P<beta>0|[1-9]\d*)))?$"
)
_SHA256_LINE_RE = re.compile(r"^(?P<digest>[0-9a-f]{64})  (?P<filename>\S+)\s*$")
_TAG_STRIP_RE = re.compile(r"^v", re.IGNORECASE)


class CheckStatus(StrEnum):
    DISABLED = "disabled"
    THROTTLED = "throttled"
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    SKIPPED = "skipped"
    ERROR = "error"


class ErrorKind(StrEnum):
    OFFLINE = "offline"
    TIMEOUT = "timeout"
    HTTP = "http"
    RATE_LIMIT = "rate_limit"
    MALFORMED = "malformed"
    MISSING_ASSET = "missing_asset"
    HASH_MISMATCH = "hash_mismatch"
    SIZE_MISMATCH = "size_mismatch"
    DOWNGRADE = "downgrade"
    SAME_VERSION = "same_version"
    UNSUPPORTED = "unsupported"
    IO = "io"
    OTHER = "other"


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    beta: int | None = None  # None => release; int => -beta.N

    @property
    def is_prerelease(self) -> bool:
        return self.beta is not None

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.beta is not None:
            return f"{base}-beta.{self.beta}"
        return base

    def __lt__(self, other: SemVer) -> bool:
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        # Release (beta=None) ranks above any -beta.N for the same X.Y.Z.
        if self.beta is None and other.beta is None:
            return False
        if self.beta is None:
            return False
        if other.beta is None:
            return True
        return self.beta < other.beta

    def __le__(self, other: SemVer) -> bool:
        return self == other or self < other

    def __gt__(self, other: SemVer) -> bool:
        return other < self

    def __ge__(self, other: SemVer) -> bool:
        return self == other or self > other


@dataclass(frozen=True)
class ReleaseManifest:
    version: str
    channel: str
    tag: str
    asset_name: str
    bytes: int
    sha256: str
    minimum_updater_version: str
    release_url: str


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    channel: str
    tag: str
    asset_name: str
    size_bytes: int
    sha256: str
    minimum_updater_version: str
    release_url: str
    installer_url: str
    checksum_url: str
    manifest_url: str
    notes: str = ""


@dataclass(frozen=True)
class CheckResult:
    status: CheckStatus
    message: str
    update: UpdateInfo | None = None
    error_kind: ErrorKind | None = None


@dataclass(frozen=True)
class DownloadResult:
    ok: bool
    message: str
    path: Path | None = None
    error_kind: ErrorKind | None = None


def parse_semver(text: str) -> SemVer | None:
    """Parse ``X.Y.Z`` or ``X.Y.Z-beta.N`` (optional leading ``v``)."""
    cleaned = _TAG_STRIP_RE.sub("", text.strip())
    match = _SEMVER_RE.fullmatch(cleaned)
    if not match:
        return None
    beta_raw = match.group("beta")
    return SemVer(
        major=int(match.group("major")),
        minor=int(match.group("minor")),
        patch=int(match.group("patch")),
        beta=int(beta_raw) if beta_raw is not None else None,
    )


def compare_semver(a: str, b: str) -> int:
    """Return -1 / 0 / 1 for a < b / equal / a > b. Raises ValueError if unparsable."""
    left = parse_semver(a)
    right = parse_semver(b)
    if left is None or right is None:
        raise ValueError(f"Invalid semver pair: {a!r}, {b!r}")
    if left < right:
        return -1
    if left > right:
        return 1
    return 0


def updates_dir() -> Path:
    path = settings.data_dir / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def updates_enabled() -> bool:
    """False when skipped via env; otherwise True when a repository identity is known.

    Unstamped (editable) builds fall back to ``DEFAULT_GITHUB_REPOSITORY`` so Settings
    can still offer a manual Check now. Automatic startup checks stay gated separately.
    """
    if os.environ.get("OPENBOSON_SKIP_UPDATE", "").strip() == "1":
        return False
    return github_repository() is not None


def github_repository() -> str | None:
    repo = _build_info.GITHUB_REPOSITORY or DEFAULT_GITHUB_REPOSITORY
    if not repo or "/" not in repo:
        return None
    return repo.strip()


def has_packaged_repository() -> bool:
    """True only when CI stamped ``_build_info.GITHUB_REPOSITORY`` into this build."""
    repo = _build_info.GITHUB_REPOSITORY
    return bool(repo and "/" in repo)


def installer_name(version: str) -> str:
    return f"OpenBoson-Setup-{version}.exe"


def checksum_name(version: str) -> str:
    return f"{installer_name(version)}.sha256"


def manifest_name(version: str) -> str:
    return f"OpenBoson-{version}.json"


def parse_checksum_file(text: str, expected_filename: str) -> str | None:
    """Return lowercase digest when the checksum line matches the contract."""
    for raw in text.splitlines():
        line = raw.strip("\r")
        if not line or line.startswith("#"):
            continue
        match = _SHA256_LINE_RE.fullmatch(line)
        if not match:
            return None
        if match.group("filename") != expected_filename:
            return None
        return match.group("digest")
    return None


def parse_manifest(data: dict[str, Any]) -> ReleaseManifest:
    required = (
        "version",
        "channel",
        "tag",
        "asset_name",
        "bytes",
        "sha256",
        "minimum_updater_version",
        "release_url",
    )
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Manifest missing fields: {', '.join(missing)}")
    digest = str(data["sha256"]).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Manifest sha256 must be lowercase 64-hex")
    size = int(data["bytes"])
    if size <= 0:
        raise ValueError("Manifest bytes must be positive")
    return ReleaseManifest(
        version=str(data["version"]).strip(),
        channel=str(data["channel"]).strip(),
        tag=str(data["tag"]).strip(),
        asset_name=str(data["asset_name"]).strip(),
        bytes=size,
        sha256=digest,
        minimum_updater_version=str(data["minimum_updater_version"]).strip(),
        release_url=str(data["release_url"]).strip(),
    )


def channel_allows_release(channel: UpdateChannel, tag: str, *, prerelease: bool) -> bool:
    """Stable ignores prereleases; beta accepts stable + ``-beta.N`` tags."""
    ver = parse_semver(tag)
    if ver is None:
        return False
    if channel == "stable":
        return not prerelease and not ver.is_prerelease
    # beta
    if not prerelease and not ver.is_prerelease:
        return True
    return ver.is_prerelease and ver.beta is not None


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def throttle_allows_check(last_check: str | None, *, now: datetime | None = None) -> bool:
    """Return True when no prior check or last check is older than 24h."""
    previous = _parse_iso(last_check)
    if previous is None:
        return True
    current = now or datetime.now(UTC)
    age = current - previous.astimezone(UTC)
    return age.total_seconds() >= CHECK_THROTTLE_HOURS * 3600


def record_update_check_time(*, when: str | None = None) -> None:
    update_settings(last_update_check=when or _iso_now())


def should_run_startup_check() -> bool:
    """True for stamped builds when startup checks are enabled and not throttled.

    Editable / unstamped trees keep Settings manual checks, but do not probe GitHub
    on every launch (and avoid network during GUI tests).
    """
    if not updates_enabled():
        return False
    if not has_packaged_repository():
        return False
    cfg = load_settings()
    if not cfg.check_updates_on_startup:
        return False
    return throttle_allows_check(cfg.last_update_check)


def _http_get(url: str, *, timeout: float) -> tuple[int, bytes, dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json, application/json, */*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — fixed HTTPS API
            status = getattr(resp, "status", 200) or 200
            headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read()
            return int(status), body, headers
    except urllib.error.HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return int(exc.code), body, headers


def _classify_http_error(status: int, body: bytes) -> CheckResult:
    text = body.decode("utf-8", errors="replace")[:200]
    if status == 403 or status == 429:
        return CheckResult(
            status=CheckStatus.ERROR,
            message=f"GitHub rate limit or forbidden ({status})",
            error_kind=ErrorKind.RATE_LIMIT,
        )
    return CheckResult(
        status=CheckStatus.ERROR,
        message=f"HTTP {status}: {text or 'request failed'}",
        error_kind=ErrorKind.HTTP,
    )


def _classify_url_error(exc: BaseException) -> CheckResult:
    name = type(exc).__name__
    msg = str(exc) or name
    lower = msg.lower()
    if "timed out" in lower or name == "TimeoutError":
        return CheckResult(
            status=CheckStatus.ERROR,
            message=f"Update check timed out: {msg}",
            error_kind=ErrorKind.TIMEOUT,
        )
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", None)
        reason_s = str(reason or exc).lower()
        if "timed out" in reason_s:
            return CheckResult(
                status=CheckStatus.ERROR,
                message=f"Update check timed out: {exc}",
                error_kind=ErrorKind.TIMEOUT,
            )
        if any(
            tok in reason_s for tok in ("name or service", "getaddrinfo", "nodename", "resolve")
        ):
            return CheckResult(
                status=CheckStatus.ERROR,
                message=f"DNS/network error: {exc}",
                error_kind=ErrorKind.OFFLINE,
            )
        return CheckResult(
            status=CheckStatus.ERROR,
            message=f"Network error: {exc}",
            error_kind=ErrorKind.OFFLINE,
        )
    return CheckResult(
        status=CheckStatus.ERROR,
        message=f"Update check failed: {msg}",
        error_kind=ErrorKind.OTHER,
    )


def _asset_map(release: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets = release.get("assets") or []
    out: dict[str, dict[str, Any]] = {}
    for asset in assets:
        name = asset.get("name")
        if isinstance(name, str):
            out[name] = asset
    return out


def _release_version(release: dict[str, Any]) -> str | None:
    tag = str(release.get("tag_name") or "")
    parsed = parse_semver(tag)
    return str(parsed) if parsed else None


def _pick_release(
    releases: list[dict[str, Any]],
    *,
    channel: UpdateChannel,
    current: SemVer,
) -> tuple[dict[str, Any], str] | CheckResult:
    """Pick the newest channel-eligible release newer than ``current``."""
    candidates: list[tuple[SemVer, dict[str, Any], str]] = []
    for release in releases:
        if release.get("draft"):
            continue
        tag = str(release.get("tag_name") or "")
        ver_s = _release_version(release)
        if ver_s is None:
            continue
        ver = parse_semver(ver_s)
        if ver is None:
            continue
        prerelease = bool(release.get("prerelease"))
        if not channel_allows_release(channel, tag, prerelease=prerelease):
            continue
        if ver <= current:
            continue
        candidates.append((ver, release, ver_s))
    if not candidates:
        # Distinguish same/older available vs nothing usable.
        any_newer_blocked = False
        for release in releases:
            if release.get("draft"):
                continue
            ver_s = _release_version(release)
            if ver_s is None:
                continue
            ver = parse_semver(ver_s)
            if ver is None:
                continue
            if ver > current:
                any_newer_blocked = True
                break
        if any_newer_blocked:
            return CheckResult(
                status=CheckStatus.UP_TO_DATE,
                message="No newer release matches the selected update channel.",
            )
        return CheckResult(
            status=CheckStatus.UP_TO_DATE,
            message=f"Already on the latest version ({current}).",
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    _ver, release, ver_s = candidates[0]
    return release, ver_s


# Hosts allowed for update metadata and installer downloads (defense in depth).
_ALLOWED_UPDATE_HOSTS = frozenset(
    {
        "api.github.com",
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
    }
)


def _validate_urls(*urls: str) -> bool:
    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            return False
        host = (parsed.hostname or "").lower()
        if host not in _ALLOWED_UPDATE_HOSTS:
            return False
    return True


def _build_update_info(
    release: dict[str, Any],
    version: str,
    manifest: ReleaseManifest,
    assets: dict[str, dict[str, Any]],
) -> UpdateInfo | CheckResult:
    expected_installer = installer_name(version)
    expected_checksum = checksum_name(version)
    expected_manifest = manifest_name(version)

    if manifest.version != version:
        return CheckResult(
            status=CheckStatus.ERROR,
            message=f"Manifest version {manifest.version!r} does not match tag version {version!r}",
            error_kind=ErrorKind.MALFORMED,
        )
    tag = str(release.get("tag_name") or "")
    if parse_semver(manifest.tag) != parse_semver(tag):
        return CheckResult(
            status=CheckStatus.ERROR,
            message=f"Manifest tag {manifest.tag!r} does not match release tag {tag!r}",
            error_kind=ErrorKind.MALFORMED,
        )
    if manifest.asset_name != expected_installer:
        return CheckResult(
            status=CheckStatus.ERROR,
            message=(
                f"Manifest asset_name {manifest.asset_name!r} "
                f"does not match expected {expected_installer!r}"
            ),
            error_kind=ErrorKind.MALFORMED,
        )

    for name in (expected_installer, expected_checksum, expected_manifest):
        if name not in assets:
            return CheckResult(
                status=CheckStatus.ERROR,
                message=f"Release is missing required asset {name}",
                error_kind=ErrorKind.MISSING_ASSET,
            )

    installer = assets[expected_installer]
    checksum = assets[expected_checksum]
    man_asset = assets[expected_manifest]
    installer_url = str(installer.get("browser_download_url") or "")
    checksum_url = str(checksum.get("browser_download_url") or "")
    manifest_url = str(man_asset.get("browser_download_url") or "")
    if not _validate_urls(installer_url, checksum_url, manifest_url, manifest.release_url):
        return CheckResult(
            status=CheckStatus.ERROR,
            message="Release asset URLs must be https",
            error_kind=ErrorKind.MALFORMED,
        )

    remote_size = installer.get("size")
    if remote_size is not None and int(remote_size) != manifest.bytes:
        return CheckResult(
            status=CheckStatus.ERROR,
            message="GitHub asset size does not match manifest bytes",
            error_kind=ErrorKind.SIZE_MISMATCH,
        )

    try:
        if compare_semver(UPDATER_VERSION, manifest.minimum_updater_version) < 0:
            return CheckResult(
                status=CheckStatus.ERROR,
                message=(
                    f"This updater ({UPDATER_VERSION}) is older than required "
                    f"minimum ({manifest.minimum_updater_version}); update manually."
                ),
                error_kind=ErrorKind.UNSUPPORTED,
            )
    except ValueError:
        return CheckResult(
            status=CheckStatus.ERROR,
            message="Invalid minimum_updater_version in manifest",
            error_kind=ErrorKind.MALFORMED,
        )

    notes = str(release.get("body") or "")
    return UpdateInfo(
        version=version,
        channel=manifest.channel,
        tag=manifest.tag,
        asset_name=manifest.asset_name,
        size_bytes=manifest.bytes,
        sha256=manifest.sha256,
        minimum_updater_version=manifest.minimum_updater_version,
        release_url=manifest.release_url,
        installer_url=installer_url,
        checksum_url=checksum_url,
        manifest_url=manifest_url,
        notes=notes,
    )


def check_for_updates(
    *,
    force: bool = False,
    current_version: str | None = None,
    channel: UpdateChannel | None = None,
    record_check: bool = True,
) -> CheckResult:
    """Query GitHub Releases for a newer installer matching the update channel.

    Never mutates the running installation. On failure returns a structured
    :class:`CheckResult` with ``status=ERROR``.
    """
    if not updates_enabled():
        return CheckResult(
            status=CheckStatus.DISABLED,
            message="Update checks are disabled for this build.",
        )

    cfg = load_settings()
    selected: UpdateChannel = channel or cfg.update_channel
    if selected not in ("stable", "beta"):
        selected = "stable"

    if not force and not throttle_allows_check(cfg.last_update_check):
        return CheckResult(
            status=CheckStatus.THROTTLED,
            message="Update check skipped (checked within the last 24 hours).",
        )

    repo = github_repository()
    if repo is None:
        return CheckResult(
            status=CheckStatus.DISABLED,
            message="Update checks are disabled (no repository identity).",
        )

    current_s = current_version or _app_version
    current = parse_semver(current_s)
    if current is None:
        return CheckResult(
            status=CheckStatus.ERROR,
            message=f"Current version is not valid semver: {current_s!r}",
            error_kind=ErrorKind.MALFORMED,
        )

    api_url = f"https://api.github.com/repos/{repo}/releases?per_page=30"
    try:
        status, body, _headers = _http_get(api_url, timeout=METADATA_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — map all network failures
        return _classify_url_error(exc)

    if record_check:
        try:
            record_update_check_time()
        except OSError as exc:
            logger.warning("Failed to persist last_update_check: %s", exc)

    if status != 200:
        return _classify_http_error(status, body)

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return CheckResult(
            status=CheckStatus.ERROR,
            message=f"Malformed releases JSON: {exc}",
            error_kind=ErrorKind.MALFORMED,
        )
    if not isinstance(payload, list):
        return CheckResult(
            status=CheckStatus.ERROR,
            message="Malformed releases JSON: expected a list",
            error_kind=ErrorKind.MALFORMED,
        )

    picked = _pick_release(payload, channel=selected, current=current)
    if isinstance(picked, CheckResult):
        return picked
    release, version = picked

    # Same-version guard (should already be filtered) — keep explicit for callers.
    remote = parse_semver(version)
    if remote is not None and remote == current:
        return CheckResult(
            status=CheckStatus.UP_TO_DATE,
            message=f"Already on version {current}.",
            error_kind=ErrorKind.SAME_VERSION,
        )
    if remote is not None and remote < current:
        return CheckResult(
            status=CheckStatus.UP_TO_DATE,
            message="Remote version is older than the installed version.",
            error_kind=ErrorKind.DOWNGRADE,
        )

    assets = _asset_map(release)
    man_name = manifest_name(version)
    if man_name not in assets:
        return CheckResult(
            status=CheckStatus.ERROR,
            message=f"Release is missing required asset {man_name}",
            error_kind=ErrorKind.MISSING_ASSET,
        )
    man_url = str(assets[man_name].get("browser_download_url") or "")
    if not _validate_urls(man_url):
        return CheckResult(
            status=CheckStatus.ERROR,
            message="Manifest download URL must be https",
            error_kind=ErrorKind.MALFORMED,
        )

    try:
        m_status, m_body, _ = _http_get(man_url, timeout=METADATA_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001
        return _classify_url_error(exc)
    if m_status != 200:
        return _classify_http_error(m_status, m_body)
    try:
        man_json = json.loads(m_body.decode("utf-8"))
        if not isinstance(man_json, dict):
            raise ValueError("manifest root must be an object")
        manifest = parse_manifest(man_json)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return CheckResult(
            status=CheckStatus.ERROR,
            message=f"Malformed release manifest: {exc}",
            error_kind=ErrorKind.MALFORMED,
        )

    built = _build_update_info(release, version, manifest, assets)
    if isinstance(built, CheckResult):
        return built

    skipped = cfg.skipped_version
    if skipped and not force and parse_semver(skipped) == parse_semver(built.version):
        return CheckResult(
            status=CheckStatus.SKIPPED,
            message=f"Version {built.version} was skipped by the user.",
            update=built,
        )

    return CheckResult(
        status=CheckStatus.UPDATE_AVAILABLE,
        message=f"Update {built.version} is available.",
        update=built,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _safe_unlink(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
    except OSError as exc:
        logger.warning("Failed to delete %s: %s", path, exc)


def download_update(info: UpdateInfo, *, dest_dir: Path | None = None) -> DownloadResult:
    """Download installer + checksum, verify size/hash, return local installer path.

    Incomplete or tampered files are deleted. The running install is never modified.
    """
    target_root = dest_dir or (updates_dir() / info.version)
    try:
        target_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return DownloadResult(
            ok=False,
            message=f"Cannot create update directory: {exc}",
            error_kind=ErrorKind.IO,
        )

    installer_path = target_root / info.asset_name
    checksum_path = target_root / f"{info.asset_name}.sha256"
    # Clear any previous partials for this version.
    _safe_unlink(installer_path)
    _safe_unlink(checksum_path)

    try:
        # Checksum file (small metadata).
        c_status, c_body, _ = _http_get(info.checksum_url, timeout=METADATA_TIMEOUT_S)
        if c_status != 200:
            return DownloadResult(
                ok=False,
                message=f"Failed to download checksum (HTTP {c_status})",
                error_kind=ErrorKind.HTTP if c_status not in (403, 429) else ErrorKind.RATE_LIMIT,
            )
        checksum_path.write_bytes(c_body)
        digest_from_file = parse_checksum_file(
            c_body.decode("utf-8", errors="replace"),
            info.asset_name,
        )
        if digest_from_file is None:
            _safe_unlink(checksum_path)
            return DownloadResult(
                ok=False,
                message="Checksum file does not match the required format",
                error_kind=ErrorKind.MALFORMED,
            )
        if digest_from_file != info.sha256.lower():
            _safe_unlink(checksum_path)
            return DownloadResult(
                ok=False,
                message="Checksum file digest does not match manifest sha256",
                error_kind=ErrorKind.HASH_MISMATCH,
            )

        # Installer (bounded by declared size).
        req = urllib.request.Request(
            info.installer_url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream,*/*"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_S) as resp:  # noqa: S310
            status = int(getattr(resp, "status", 200) or 200)
            if status != 200:
                return DownloadResult(
                    ok=False,
                    message=f"Failed to download installer (HTTP {status})",
                    error_kind=ErrorKind.HTTP,
                )
            content_length = resp.headers.get("Content-Length")
            if content_length is not None and int(content_length) != info.size_bytes:
                return DownloadResult(
                    ok=False,
                    message="Installer Content-Length does not match manifest bytes",
                    error_kind=ErrorKind.SIZE_MISMATCH,
                )
            written = 0
            hasher = hashlib.sha256()
            with installer_path.open("wb") as out:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > info.size_bytes:
                        out.close()
                        _safe_unlink(installer_path)
                        _safe_unlink(checksum_path)
                        return DownloadResult(
                            ok=False,
                            message="Downloaded installer exceeded declared size",
                            error_kind=ErrorKind.SIZE_MISMATCH,
                        )
                    hasher.update(chunk)
                    out.write(chunk)
                    out.flush()

        if written != info.size_bytes:
            _safe_unlink(installer_path)
            _safe_unlink(checksum_path)
            return DownloadResult(
                ok=False,
                message=f"Installer size {written} does not match manifest {info.size_bytes}",
                error_kind=ErrorKind.SIZE_MISMATCH,
            )

        digest = hasher.hexdigest()
        if digest != info.sha256.lower():
            _safe_unlink(installer_path)
            _safe_unlink(checksum_path)
            return DownloadResult(
                ok=False,
                message="Installer SHA-256 does not match manifest",
                error_kind=ErrorKind.HASH_MISMATCH,
            )

        # Re-hash from disk as a final integrity check before launch.
        if _sha256_file(installer_path) != info.sha256.lower():
            _safe_unlink(installer_path)
            _safe_unlink(checksum_path)
            return DownloadResult(
                ok=False,
                message="Installer failed on-disk hash verification",
                error_kind=ErrorKind.HASH_MISMATCH,
            )

        return DownloadResult(ok=True, message="Download verified.", path=installer_path)
    except Exception as exc:  # noqa: BLE001 — leave install untouched
        _safe_unlink(installer_path)
        _safe_unlink(checksum_path)
        classified = _classify_url_error(exc)
        return DownloadResult(
            ok=False,
            message=classified.message,
            error_kind=classified.error_kind or ErrorKind.OTHER,
        )


def launch_installer(path: Path | str) -> None:
    """Start the Windows installer executable. Caller must confirm with the user first."""
    exe = Path(path)
    if not exe.is_file():
        raise FileNotFoundError(f"Installer not found: {exe}")
    if sys.platform != "win32":
        raise RuntimeError("Installer launch is only supported on Windows")
    # Detached process so the updater does not wait on the installer UI.
    subprocess.Popen(  # noqa: S603 — path validated as local file
        [str(exe)],
        close_fds=True,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


def skip_version(version: str) -> None:
    update_settings(skipped_version=version)


def clear_skipped_version() -> None:
    update_settings(skipped_version=None)


__all__ = [
    "UPDATER_VERSION",
    "CheckResult",
    "CheckStatus",
    "DownloadResult",
    "ErrorKind",
    "ReleaseManifest",
    "SemVer",
    "UpdateInfo",
    "channel_allows_release",
    "check_for_updates",
    "checksum_name",
    "clear_skipped_version",
    "compare_semver",
    "download_update",
    "github_repository",
    "has_packaged_repository",
    "installer_name",
    "launch_installer",
    "manifest_name",
    "parse_checksum_file",
    "parse_manifest",
    "parse_semver",
    "record_update_check_time",
    "should_run_startup_check",
    "skip_version",
    "throttle_allows_check",
    "updates_dir",
    "updates_enabled",
]
