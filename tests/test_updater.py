"""Unit tests for the GitHub Releases updater (mocked HTTP)."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime, timedelta

import pytest

from openboson import updater as upd
from openboson.settings_store import load_settings, update_settings


class _FakeResponse:
    def __init__(self, body: bytes, *, status: int = 200, headers: dict | None = None):
        self._body = body
        self.status = status
        self.headers = headers or {}

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            data, self._body = self._body, b""
            return data
        data, self._body = self._body[:n], self._body[n:]
        return data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _sha256_hex(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def repo_enabled(monkeypatch, isolated_home):
    monkeypatch.setattr(upd._build_info, "GITHUB_REPOSITORY", "openboson/openboson")
    monkeypatch.delenv("OPENBOSON_SKIP_UPDATE", raising=False)
    yield isolated_home


def test_parse_semver_and_compare():
    assert str(upd.parse_semver("v1.2.3")) == "1.2.3"
    assert str(upd.parse_semver("1.2.3-beta.2")) == "1.2.3-beta.2"
    assert upd.parse_semver("1.2") is None
    assert upd.compare_semver("1.0.0", "1.0.1") == -1
    assert upd.compare_semver("1.0.1", "1.0.0") == 1
    assert upd.compare_semver("1.0.0", "1.0.0") == 0
    # Release ranks above prerelease for same X.Y.Z.
    assert upd.compare_semver("1.0.0-beta.9", "1.0.0") == -1
    assert upd.compare_semver("1.0.1-beta.1", "1.0.0") == 1


def test_channel_allows_release():
    assert upd.channel_allows_release("stable", "v1.2.3", prerelease=False)
    assert not upd.channel_allows_release("stable", "v1.2.3-beta.1", prerelease=True)
    assert not upd.channel_allows_release("stable", "v1.2.3", prerelease=True)
    assert upd.channel_allows_release("beta", "v1.2.3", prerelease=False)
    assert upd.channel_allows_release("beta", "v1.2.3-beta.1", prerelease=True)
    assert not upd.channel_allows_release("beta", "v1.2.3-rc.1", prerelease=True)


def test_parse_checksum_contract():
    name = "OpenBoson-Setup-1.2.3.exe"
    digest = "a" * 64
    assert upd.parse_checksum_file(f"{digest}  {name}\n", name) == digest
    assert upd.parse_checksum_file(f"{digest} {name}\n", name) is None  # one space
    assert upd.parse_checksum_file(f"{digest.upper()}  {name}\n", name) is None
    assert upd.parse_checksum_file(f"{digest}  other.exe\n", name) is None


def test_updates_disabled_without_repo(monkeypatch, isolated_home):
    monkeypatch.setattr(upd._build_info, "GITHUB_REPOSITORY", None)
    assert not upd.updates_enabled()
    result = upd.check_for_updates(force=True)
    assert result.status == upd.CheckStatus.DISABLED


def test_updates_disabled_via_env(repo_enabled, monkeypatch):
    monkeypatch.setenv("OPENBOSON_SKIP_UPDATE", "1")
    assert not upd.updates_enabled()
    result = upd.check_for_updates(force=True)
    assert result.status == upd.CheckStatus.DISABLED


def _release(
    *,
    version: str,
    prerelease: bool = False,
    installer: bytes | None = None,
    omit_manifest: bool = False,
    omit_installer: bool = False,
    size_override: int | None = None,
):
    payload = installer if installer is not None else b"installer-bytes"
    digest = _sha256_hex(payload)
    size = size_override if size_override is not None else len(payload)
    assets = []
    if not omit_installer:
        assets.append(
            {
                "name": upd.installer_name(version),
                "browser_download_url": f"https://objects.githubusercontent.com/{upd.installer_name(version)}",
                "size": size,
            }
        )
    assets.append(
        {
            "name": upd.checksum_name(version),
            "browser_download_url": f"https://objects.githubusercontent.com/{upd.checksum_name(version)}",
            "size": 80,
        }
    )
    if not omit_manifest:
        assets.append(
            {
                "name": upd.manifest_name(version),
                "browser_download_url": f"https://objects.githubusercontent.com/{upd.manifest_name(version)}",
                "size": 200,
            }
        )
    return (
        {
            "tag_name": f"v{version}",
            "prerelease": prerelease,
            "draft": False,
            "html_url": f"https://github.com/openboson/openboson/releases/tag/v{version}",
            "body": f"Notes for {version}",
            "assets": assets,
        },
        payload,
        digest,
        size,
    )


def _manifest(version: str, digest: str, size: int, *, channel: str = "stable") -> dict:
    return {
        "version": version,
        "channel": channel,
        "tag": f"v{version}",
        "asset_name": upd.installer_name(version),
        "bytes": size,
        "sha256": digest,
        "minimum_updater_version": "1.0.0",
        "release_url": f"https://github.com/openboson/openboson/releases/tag/v{version}",
    }


def _install_urlopen(monkeypatch, mapping: dict[str, tuple[int, bytes, dict]]):
    from urllib.error import HTTPError, URLError

    def fake_urlopen(req, timeout=None):  # noqa: ANN001
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url not in mapping:
            raise URLError(f"unexpected url {url}")
        status, body, headers = mapping[url]
        if status >= 400:
            raise HTTPError(url, status, "err", hdrs=None, fp=io.BytesIO(body))
        return _FakeResponse(body, status=status, headers=headers)

    monkeypatch.setattr(upd.urllib.request, "urlopen", fake_urlopen)


def test_check_finds_stable_update(repo_enabled, monkeypatch):
    version = "0.3.0"
    release, payload, digest, size = _release(version=version)
    releases_url = "https://api.github.com/repos/openboson/openboson/releases?per_page=30"
    man_url = f"https://objects.githubusercontent.com/{upd.manifest_name(version)}"
    mapping = {
        releases_url: (200, json.dumps([release]).encode(), {}),
        man_url: (200, json.dumps(_manifest(version, digest, size)).encode(), {}),
    }
    _install_urlopen(monkeypatch, mapping)
    update_settings(update_channel="stable")
    result = upd.check_for_updates(force=True, current_version="0.2.0")
    assert result.status == upd.CheckStatus.UPDATE_AVAILABLE
    assert result.update is not None
    assert result.update.version == "0.3.0"
    assert result.update.sha256 == digest
    assert load_settings().last_update_check is not None


def test_stable_ignores_beta_prerelease(repo_enabled, monkeypatch):
    version = "0.3.0-beta.1"
    release, _payload, _digest, _size = _release(version=version, prerelease=True)
    releases_url = "https://api.github.com/repos/openboson/openboson/releases?per_page=30"
    mapping = {
        releases_url: (200, json.dumps([release]).encode(), {}),
    }
    _install_urlopen(monkeypatch, mapping)
    update_settings(update_channel="stable")
    result = upd.check_for_updates(force=True, current_version="0.2.0")
    assert result.status == upd.CheckStatus.UP_TO_DATE


def test_beta_accepts_beta_prerelease(repo_enabled, monkeypatch):
    version = "0.3.0-beta.1"
    release, _payload, digest, size = _release(version=version, prerelease=True)
    releases_url = "https://api.github.com/repos/openboson/openboson/releases?per_page=30"
    man_url = f"https://objects.githubusercontent.com/{upd.manifest_name(version)}"
    mapping = {
        releases_url: (200, json.dumps([release]).encode(), {}),
        man_url: (
            200,
            json.dumps(_manifest(version, digest, size, channel="beta")).encode(),
            {},
        ),
    }
    _install_urlopen(monkeypatch, mapping)
    update_settings(update_channel="beta")
    result = upd.check_for_updates(force=True, current_version="0.2.0")
    assert result.status == upd.CheckStatus.UPDATE_AVAILABLE
    assert result.update is not None
    assert result.update.version == version


def test_throttle_blocks_repeat_check(repo_enabled, monkeypatch):
    from urllib.error import URLError

    now = datetime.now(UTC).replace(microsecond=0)
    update_settings(last_update_check=now.isoformat().replace("+00:00", "Z"))
    result = upd.check_for_updates(force=False, current_version="0.2.0")
    assert result.status == upd.CheckStatus.THROTTLED

    old = (now - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
    update_settings(last_update_check=old)

    def boom(req, timeout=None):  # noqa: ANN001
        raise URLError("timed out")

    monkeypatch.setattr(upd.urllib.request, "urlopen", boom)
    result2 = upd.check_for_updates(force=False, current_version="0.2.0")
    assert result2.status == upd.CheckStatus.ERROR
    assert result2.error_kind == upd.ErrorKind.TIMEOUT


def test_skip_version_on_startup_style_check(repo_enabled, monkeypatch):
    version = "0.3.0"
    release, _payload, digest, size = _release(version=version)
    releases_url = "https://api.github.com/repos/openboson/openboson/releases?per_page=30"
    man_url = f"https://objects.githubusercontent.com/{upd.manifest_name(version)}"
    mapping = {
        releases_url: (200, json.dumps([release]).encode(), {}),
        man_url: (200, json.dumps(_manifest(version, digest, size)).encode(), {}),
    }
    _install_urlopen(monkeypatch, mapping)
    update_settings(skipped_version="0.3.0", last_update_check=None)
    result = upd.check_for_updates(force=False, current_version="0.2.0")
    assert result.status == upd.CheckStatus.SKIPPED
    # Forced check surfaces the update again.
    result2 = upd.check_for_updates(force=True, current_version="0.2.0")
    assert result2.status == upd.CheckStatus.UPDATE_AVAILABLE


def test_missing_asset_failure(repo_enabled, monkeypatch):
    version = "0.3.0"
    release, _payload, digest, size = _release(version=version, omit_installer=True)
    releases_url = "https://api.github.com/repos/openboson/openboson/releases?per_page=30"
    man_url = f"https://objects.githubusercontent.com/{upd.manifest_name(version)}"
    mapping = {
        releases_url: (200, json.dumps([release]).encode(), {}),
        man_url: (200, json.dumps(_manifest(version, digest, size)).encode(), {}),
    }
    _install_urlopen(monkeypatch, mapping)
    result = upd.check_for_updates(force=True, current_version="0.2.0")
    assert result.status == upd.CheckStatus.ERROR
    assert result.error_kind == upd.ErrorKind.MISSING_ASSET


def test_malformed_manifest(repo_enabled, monkeypatch):
    version = "0.3.0"
    release, _payload, _digest, _size = _release(version=version)
    releases_url = "https://api.github.com/repos/openboson/openboson/releases?per_page=30"
    man_url = f"https://objects.githubusercontent.com/{upd.manifest_name(version)}"
    mapping = {
        releases_url: (200, json.dumps([release]).encode(), {}),
        man_url: (200, b"{not-json", {}),
    }
    _install_urlopen(monkeypatch, mapping)
    result = upd.check_for_updates(force=True, current_version="0.2.0")
    assert result.status == upd.CheckStatus.ERROR
    assert result.error_kind == upd.ErrorKind.MALFORMED


def test_rate_limit_failure(repo_enabled, monkeypatch):
    releases_url = "https://api.github.com/repos/openboson/openboson/releases?per_page=30"
    mapping = {releases_url: (403, b"rate limited", {})}
    _install_urlopen(monkeypatch, mapping)
    result = upd.check_for_updates(force=True, current_version="0.2.0")
    assert result.status == upd.CheckStatus.ERROR
    assert result.error_kind == upd.ErrorKind.RATE_LIMIT


def test_download_verifies_hash_and_deletes_tampered(repo_enabled, monkeypatch, tmp_path):
    version = "0.3.0"
    payload = b"good-installer-content"
    digest = _sha256_hex(payload)
    size = len(payload)
    info = upd.UpdateInfo(
        version=version,
        channel="stable",
        tag=f"v{version}",
        asset_name=upd.installer_name(version),
        size_bytes=size,
        sha256=digest,
        minimum_updater_version="1.0.0",
        release_url="https://github.com/openboson/openboson/releases/tag/v0.3.0",
        installer_url=f"https://objects.githubusercontent.com/{upd.installer_name(version)}",
        checksum_url=f"https://objects.githubusercontent.com/{upd.checksum_name(version)}",
        manifest_url=f"https://objects.githubusercontent.com/{upd.manifest_name(version)}",
    )
    checksum_body = f"{digest}  {info.asset_name}\n".encode()
    mapping = {
        info.checksum_url: (200, checksum_body, {}),
        info.installer_url: (200, payload, {"Content-Length": str(size)}),
    }
    _install_urlopen(monkeypatch, mapping)
    dest = tmp_path / "updates" / version
    result = upd.download_update(info, dest_dir=dest)
    assert result.ok
    assert result.path is not None
    assert result.path.is_file()
    assert result.path.read_bytes() == payload

    # Tampered download is deleted.
    bad = upd.UpdateInfo(**{**info.__dict__, "sha256": "c" * 64})
    mapping_bad = {
        bad.checksum_url: (200, f"{'c' * 64}  {bad.asset_name}\n".encode(), {}),
        bad.installer_url: (200, payload, {"Content-Length": str(size)}),
    }
    _install_urlopen(monkeypatch, mapping_bad)
    result_bad = upd.download_update(bad, dest_dir=dest)
    assert not result_bad.ok
    assert result_bad.error_kind == upd.ErrorKind.HASH_MISMATCH
    assert not (dest / bad.asset_name).exists()


def test_download_size_mismatch_deletes(repo_enabled, monkeypatch, tmp_path):
    version = "0.3.0"
    payload = b"abc"
    digest = _sha256_hex(payload)
    info = upd.UpdateInfo(
        version=version,
        channel="stable",
        tag=f"v{version}",
        asset_name=upd.installer_name(version),
        size_bytes=10,
        sha256=digest,
        minimum_updater_version="1.0.0",
        release_url="https://github.com/x/y/releases/tag/v0.3.0",
        installer_url=f"https://objects.githubusercontent.com/{upd.installer_name(version)}",
        checksum_url=f"https://objects.githubusercontent.com/{upd.checksum_name(version)}",
        manifest_url=f"https://objects.githubusercontent.com/{upd.manifest_name(version)}",
    )
    mapping = {
        info.checksum_url: (200, f"{digest}  {info.asset_name}\n".encode(), {}),
        info.installer_url: (200, payload, {"Content-Length": "3"}),
    }
    _install_urlopen(monkeypatch, mapping)
    dest = tmp_path / version
    result = upd.download_update(info, dest_dir=dest)
    assert not result.ok
    assert result.error_kind == upd.ErrorKind.SIZE_MISMATCH
    assert not (dest / info.asset_name).exists()


def test_should_run_startup_check(repo_enabled, monkeypatch):
    update_settings(check_updates_on_startup=True, last_update_check=None)
    assert upd.should_run_startup_check() is True
    update_settings(check_updates_on_startup=False)
    assert upd.should_run_startup_check() is False
    update_settings(check_updates_on_startup=True)
    monkeypatch.setenv("OPENBOSON_SKIP_UPDATE", "1")
    assert upd.should_run_startup_check() is False


def test_launch_installer_requires_windows(monkeypatch, tmp_path):
    exe = tmp_path / "OpenBoson-Setup-0.3.0.exe"
    exe.write_bytes(b"mz")
    monkeypatch.setattr(upd.sys, "platform", "linux")
    with pytest.raises(RuntimeError):
        upd.launch_installer(exe)


def test_launch_installer_windows(monkeypatch, tmp_path):
    exe = tmp_path / "OpenBoson-Setup-0.3.0.exe"
    exe.write_bytes(b"mz")
    monkeypatch.setattr(upd.sys, "platform", "win32")
    called: list = []

    def fake_popen(args, **kwargs):  # noqa: ANN001
        called.append((args, kwargs))
        return object()

    monkeypatch.setattr(upd.subprocess, "Popen", fake_popen)
    upd.launch_installer(exe)
    assert called and called[0][0] == [str(exe)]


def test_same_version_is_up_to_date(repo_enabled, monkeypatch):
    version = "0.2.0"
    release, _payload, _digest, _size = _release(version=version)
    releases_url = "https://api.github.com/repos/openboson/openboson/releases?per_page=30"
    mapping = {releases_url: (200, json.dumps([release]).encode(), {})}
    _install_urlopen(monkeypatch, mapping)
    result = upd.check_for_updates(force=True, current_version="0.2.0")
    assert result.status == upd.CheckStatus.UP_TO_DATE


def test_dns_failure(repo_enabled, monkeypatch):
    from urllib.error import URLError

    def boom(req, timeout=None):  # noqa: ANN001
        raise URLError("getaddrinfo failed")

    monkeypatch.setattr(upd.urllib.request, "urlopen", boom)
    result = upd.check_for_updates(force=True, current_version="0.2.0")
    assert result.status == upd.CheckStatus.ERROR
    assert result.error_kind == upd.ErrorKind.OFFLINE


def test_validate_urls_requires_https_github_hosts():
    assert upd._validate_urls("https://api.github.com/repos/x/y/releases")
    assert upd._validate_urls("https://objects.githubusercontent.com/path")
    assert not upd._validate_urls("http://api.github.com/repos/x/y")
    assert not upd._validate_urls("https://evil.example/installer.exe")
    assert not upd._validate_urls("https://github.com.evil.example/x")
