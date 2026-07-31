"""Hot-loadable content registry for bundled, local, and pack content.

The registry is the single source of truth for question banks and labs used by
the GUI and FastAPI layers. It merges:

* bundled demo banks/labs (highest precedence)
* legacy loose files under ``~/.openboson/banks`` and ``~/.openboson/labs``
* distributable packs under ``~/.openboson/packs/{pack_id}/`` with ``pack.yaml``

Collision policy: bundled content always wins. A pack that collides on any
question id or ``lab_id`` is rejected as a whole. Legacy loose files that
collide are rejected individually. No silent overrides.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from openboson import __version__
from openboson.bank_loader import BankLoaderError, load_exam_bank, merge_banks
from openboson.bank_schema import ExamBank, QuestionPool
from openboson.config import settings
from openboson.netsim.lab_loader import LabLoaderError, load_lab
from openboson.netsim.lab_schema import LabBank
from openboson.resource_paths import bundled_banks_dir, bundled_labs_dir

logger = logging.getLogger(__name__)

# Security / size limits
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MiB
MAX_QUESTIONS_PER_PACK = 5000
MAX_LABS_PER_PACK = 100
MAX_DEVICES_PER_LAB = 50
MAX_TASKS_PER_LAB = 200

PROVENANCE_BUNDLED = "bundled"
PROVENANCE_LOCAL = "local/unverified"
PROVENANCE_PACK_PREFIX = "pack:"

_FORBIDDEN_MANIFEST_KEYS = frozenset(
    {
        "hooks",
        "scripts",
        "exec",
        "commands",
        "install",
        "install_script",
        "post_install",
        "pre_install",
        "entrypoint",
        "run",
        "executable",
        "shell",
        "cmd",
        "on_load",
        "on_install",
    }
)

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_ABS_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/)")
_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")

_REGISTRY: ContentRegistry | None = None


@dataclass(frozen=True)
class AcceptedContent:
    """One successfully loaded content file (or pack as a unit marker)."""

    path: str
    provenance: str
    kind: str  # "bank" | "lab" | "pack"


@dataclass(frozen=True)
class RejectedContent:
    """One rejected file or pack with a human-readable reason."""

    path: str
    provenance: str
    reason: str


@dataclass
class ContentDiagnostics:
    """Outcome of a registry scan / refresh."""

    accepted: list[AcceptedContent] = field(default_factory=list)
    rejected: list[RejectedContent] = field(default_factory=list)

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "accepted": [asdict(a) for a in self.accepted],
            "rejected": [asdict(r) for r in self.rejected],
        }


@dataclass(frozen=True)
class _FileFingerprint:
    path: str
    mtime_ns: int
    size: int


@dataclass
class _LoadedState:
    banks: list[ExamBank] = field(default_factory=list)
    labs: list[LabBank] = field(default_factory=list)
    pool: QuestionPool | None = None
    diagnostics: ContentDiagnostics = field(default_factory=ContentDiagnostics)
    fingerprints: tuple[_FileFingerprint, ...] = ()


class ContentRegistry:
    """Discover, validate, and cache merged banks/labs from all sources."""

    def __init__(self) -> None:
        self._state: _LoadedState | None = None

    def refresh(self) -> ContentDiagnostics:
        """Invalidate cache and rescan all content sources."""
        self._state = None
        return self._ensure_loaded().diagnostics

    def diagnostics(self) -> ContentDiagnostics:
        return self._ensure_loaded().diagnostics

    def banks(self) -> list[ExamBank]:
        return list(self._ensure_loaded().banks)

    def labs(self) -> list[LabBank]:
        return list(self._ensure_loaded().labs)

    def question_pool(self) -> QuestionPool:
        state = self._ensure_loaded()
        if state.pool is None:
            state.pool = merge_banks(state.banks)
        return state.pool

    def _ensure_loaded(self) -> _LoadedState:
        fps = self._collect_fingerprints()
        if self._state is not None and self._state.fingerprints == fps:
            return self._state
        state = self._scan()
        state.fingerprints = fps
        state.pool = merge_banks(state.banks)
        self._state = state
        return state

    def _collect_fingerprints(self) -> tuple[_FileFingerprint, ...]:
        paths: list[Path] = []
        for root in (bundled_banks_dir(), bundled_labs_dir()):
            paths.extend(_yaml_files(root))
        for root in (settings.banks_dir, settings.labs_dir):
            if root.is_dir():
                paths.extend(_yaml_files(root))
        packs_root = settings.packs_dir
        if packs_root.is_dir():
            for pack_dir in sorted(p for p in packs_root.iterdir() if p.is_dir()):
                paths.extend(sorted(pack_dir.rglob("*.yaml")))
                paths.extend(sorted(pack_dir.rglob("*.yml")))
        out: list[_FileFingerprint] = []
        for path in sorted({p.resolve() for p in paths}):
            try:
                st = path.stat()
            except OSError:
                continue
            out.append(_FileFingerprint(path=str(path), mtime_ns=st.st_mtime_ns, size=st.st_size))
        return tuple(out)

    def _scan(self) -> _LoadedState:
        state = _LoadedState()
        seen_q: set[str] = set()
        seen_labs: set[str] = set()

        self._load_bundled_banks(state, seen_q)
        self._load_bundled_labs(state, seen_labs)
        self._load_legacy_banks(state, seen_q)
        self._load_legacy_labs(state, seen_labs)
        self._load_packs(state, seen_q, seen_labs)

        logger.info(
            "Content registry: %d banks, %d labs, %d accepted, %d rejected",
            len(state.banks),
            len(state.labs),
            state.diagnostics.accepted_count,
            state.diagnostics.rejected_count,
        )
        return state

    def _load_bundled_banks(self, state: _LoadedState, seen_q: set[str]) -> None:
        root = bundled_banks_dir()
        for path in _yaml_files(root):
            try:
                bank = load_exam_bank(path)
            except BankLoaderError as exc:
                state.diagnostics.rejected.append(
                    RejectedContent(str(path), PROVENANCE_BUNDLED, str(exc))
                )
                continue
            except Exception as exc:  # noqa: BLE001
                state.diagnostics.rejected.append(
                    RejectedContent(str(path), PROVENANCE_BUNDLED, f"Failed to load bank: {exc}")
                )
                continue
            for q in bank.questions:
                seen_q.add(q.id)
            state.banks.append(bank)
            state.diagnostics.accepted.append(
                AcceptedContent(str(path), PROVENANCE_BUNDLED, "bank")
            )

    def _load_bundled_labs(self, state: _LoadedState, seen_labs: set[str]) -> None:
        root = bundled_labs_dir()
        for path in _yaml_files(root):
            try:
                lab = load_lab(path)
            except LabLoaderError as exc:
                state.diagnostics.rejected.append(
                    RejectedContent(str(path), PROVENANCE_BUNDLED, str(exc))
                )
                continue
            except Exception as exc:  # noqa: BLE001
                state.diagnostics.rejected.append(
                    RejectedContent(str(path), PROVENANCE_BUNDLED, f"Failed to load lab: {exc}")
                )
                continue
            limit_err = _lab_limit_errors(lab)
            if limit_err:
                state.diagnostics.rejected.append(
                    RejectedContent(str(path), PROVENANCE_BUNDLED, limit_err)
                )
                continue
            seen_labs.add(lab.lab_id)
            state.labs.append(lab)
            state.diagnostics.accepted.append(AcceptedContent(str(path), PROVENANCE_BUNDLED, "lab"))

    def _load_legacy_banks(self, state: _LoadedState, seen_q: set[str]) -> None:
        root = settings.banks_dir
        if not root.is_dir():
            return
        for path in _yaml_files(root):
            size_err = _check_file_size(path)
            if size_err:
                state.diagnostics.rejected.append(
                    RejectedContent(str(path), PROVENANCE_LOCAL, size_err)
                )
                continue
            bank, err = _try_load_bank(path)
            if err is not None:
                state.diagnostics.rejected.append(RejectedContent(str(path), PROVENANCE_LOCAL, err))
                continue
            assert bank is not None
            collisions = sorted({q.id for q in bank.questions if q.id in seen_q})
            if collisions:
                preview = ", ".join(collisions[:5])
                more = f" (+{len(collisions) - 5} more)" if len(collisions) > 5 else ""
                state.diagnostics.rejected.append(
                    RejectedContent(
                        str(path),
                        PROVENANCE_LOCAL,
                        f"Question id collision with existing content: {preview}{more}",
                    )
                )
                continue
            for q in bank.questions:
                seen_q.add(q.id)
            state.banks.append(bank)
            state.diagnostics.accepted.append(AcceptedContent(str(path), PROVENANCE_LOCAL, "bank"))

    def _load_legacy_labs(self, state: _LoadedState, seen_labs: set[str]) -> None:
        root = settings.labs_dir
        if not root.is_dir():
            return
        for path in _yaml_files(root):
            size_err = _check_file_size(path)
            if size_err:
                state.diagnostics.rejected.append(
                    RejectedContent(str(path), PROVENANCE_LOCAL, size_err)
                )
                continue
            lab, err = _try_load_lab(path)
            if err is not None:
                state.diagnostics.rejected.append(RejectedContent(str(path), PROVENANCE_LOCAL, err))
                continue
            assert lab is not None
            limit_err = _lab_limit_errors(lab)
            if limit_err:
                state.diagnostics.rejected.append(
                    RejectedContent(str(path), PROVENANCE_LOCAL, limit_err)
                )
                continue
            if lab.lab_id in seen_labs:
                state.diagnostics.rejected.append(
                    RejectedContent(
                        str(path),
                        PROVENANCE_LOCAL,
                        f"lab_id collision with existing content: {lab.lab_id}",
                    )
                )
                continue
            seen_labs.add(lab.lab_id)
            state.labs.append(lab)
            state.diagnostics.accepted.append(AcceptedContent(str(path), PROVENANCE_LOCAL, "lab"))

    def _load_packs(
        self,
        state: _LoadedState,
        seen_q: set[str],
        seen_labs: set[str],
    ) -> None:
        packs_root = settings.packs_dir
        if not packs_root.is_dir():
            return
        for pack_dir in sorted(p for p in packs_root.iterdir() if p.is_dir()):
            self._load_one_pack(pack_dir, state, seen_q, seen_labs)

    def _load_one_pack(
        self,
        pack_dir: Path,
        state: _LoadedState,
        seen_q: set[str],
        seen_labs: set[str],
    ) -> None:
        manifest_path = pack_dir / "pack.yaml"
        provenance = f"{PROVENANCE_PACK_PREFIX}{pack_dir.name}"
        if not manifest_path.is_file():
            state.diagnostics.rejected.append(
                RejectedContent(str(pack_dir), provenance, "Missing pack.yaml manifest")
            )
            return

        try:
            manifest = _load_pack_manifest(manifest_path, pack_dir)
        except PackError as exc:
            state.diagnostics.rejected.append(
                RejectedContent(str(manifest_path), provenance, str(exc))
            )
            return

        provenance = f"{PROVENANCE_PACK_PREFIX}{manifest['id']}"
        if not _version_satisfies(manifest["min_app_version"], __version__):
            state.diagnostics.rejected.append(
                RejectedContent(
                    str(manifest_path),
                    provenance,
                    (
                        f"Pack requires app version >= {manifest['min_app_version']}, "
                        f"running {__version__}"
                    ),
                )
            )
            return

        banks: list[ExamBank] = []
        labs: list[LabBank] = []
        accepted_paths: list[tuple[str, str]] = []  # path, kind

        for entry in manifest["files"]:
            rel = entry["path"]
            expected_hash = entry["sha256"]
            file_path = (pack_dir / rel).resolve()
            try:
                file_path.relative_to(pack_dir.resolve())
            except ValueError:
                state.diagnostics.rejected.append(
                    RejectedContent(
                        str(manifest_path),
                        provenance,
                        f"File escapes pack directory: {rel}",
                    )
                )
                return

            if not file_path.is_file():
                state.diagnostics.rejected.append(
                    RejectedContent(
                        str(manifest_path),
                        provenance,
                        f"Listed file missing: {rel}",
                    )
                )
                return

            size_err = _check_file_size(file_path)
            if size_err:
                state.diagnostics.rejected.append(
                    RejectedContent(str(file_path), provenance, size_err)
                )
                return

            actual = _sha256_file(file_path)
            if actual.lower() != expected_hash.lower():
                state.diagnostics.rejected.append(
                    RejectedContent(
                        str(file_path),
                        provenance,
                        f"SHA-256 mismatch for {rel} (tampered or corrupt)",
                    )
                )
                return

            kind, bank, lab, err = _load_pack_content_file(file_path)
            if err is not None:
                state.diagnostics.rejected.append(RejectedContent(str(file_path), provenance, err))
                return
            if kind == "bank" and bank is not None:
                banks.append(bank)
                accepted_paths.append((str(file_path), "bank"))
            elif kind == "lab" and lab is not None:
                labs.append(lab)
                accepted_paths.append((str(file_path), "lab"))

        q_count = sum(len(b.questions) for b in banks)
        if q_count > MAX_QUESTIONS_PER_PACK:
            state.diagnostics.rejected.append(
                RejectedContent(
                    str(pack_dir),
                    provenance,
                    f"Pack exceeds question limit ({q_count} > {MAX_QUESTIONS_PER_PACK})",
                )
            )
            return
        if len(labs) > MAX_LABS_PER_PACK:
            state.diagnostics.rejected.append(
                RejectedContent(
                    str(pack_dir),
                    provenance,
                    f"Pack exceeds lab limit ({len(labs)} > {MAX_LABS_PER_PACK})",
                )
            )
            return

        for lab in labs:
            limit_err = _lab_limit_errors(lab)
            if limit_err:
                state.diagnostics.rejected.append(
                    RejectedContent(str(pack_dir), provenance, limit_err)
                )
                return

        q_ids = [q.id for b in banks for q in b.questions]
        lab_ids = [lab.lab_id for lab in labs]
        q_collisions = sorted({qid for qid in q_ids if qid in seen_q})
        lab_collisions = sorted({lid for lid in lab_ids if lid in seen_labs})
        # Also reject internal duplicates within the pack.
        if len(q_ids) != len(set(q_ids)):
            state.diagnostics.rejected.append(
                RejectedContent(
                    str(pack_dir),
                    provenance,
                    "Duplicate question ids within pack",
                )
            )
            return
        if len(lab_ids) != len(set(lab_ids)):
            state.diagnostics.rejected.append(
                RejectedContent(
                    str(pack_dir),
                    provenance,
                    "Duplicate lab_id values within pack",
                )
            )
            return
        if q_collisions or lab_collisions:
            parts: list[str] = []
            if q_collisions:
                preview = ", ".join(q_collisions[:5])
                more = f" (+{len(q_collisions) - 5} more)" if len(q_collisions) > 5 else ""
                parts.append(f"question ids: {preview}{more}")
            if lab_collisions:
                preview = ", ".join(lab_collisions[:5])
                more = f" (+{len(lab_collisions) - 5} more)" if len(lab_collisions) > 5 else ""
                parts.append(f"lab_ids: {preview}{more}")
            state.diagnostics.rejected.append(
                RejectedContent(
                    str(pack_dir),
                    provenance,
                    "Pack rejected due to collision with existing content ("
                    + "; ".join(parts)
                    + ")",
                )
            )
            return

        for qid in q_ids:
            seen_q.add(qid)
        for lid in lab_ids:
            seen_labs.add(lid)
        state.banks.extend(banks)
        state.labs.extend(labs)
        state.diagnostics.accepted.append(AcceptedContent(str(pack_dir), provenance, "pack"))
        for path, kind in accepted_paths:
            state.diagnostics.accepted.append(AcceptedContent(path, provenance, kind))


class PackError(Exception):
    """Raised when a pack manifest is invalid or unsafe."""


def get_registry() -> ContentRegistry:
    """Return the process-wide content registry singleton."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ContentRegistry()
    return _REGISTRY


def reset_registry() -> None:
    """Drop the singleton (for tests)."""
    global _REGISTRY
    _REGISTRY = None


def _yaml_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(list(directory.glob("*.yaml")) + list(directory.glob("*.yml")))


def _check_file_size(path: Path) -> str | None:
    try:
        size = path.stat().st_size
    except OSError as exc:
        return f"Cannot stat file: {exc}"
    if size > MAX_FILE_BYTES:
        return f"File exceeds size limit ({size} > {MAX_FILE_BYTES} bytes)"
    return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _try_load_bank(path: Path) -> tuple[ExamBank | None, str | None]:
    size_err = _check_file_size(path)
    if size_err:
        return None, size_err
    try:
        return load_exam_bank(path), None
    except BankLoaderError as exc:
        return None, str(exc)
    except Exception as exc:  # noqa: BLE001 — surface unexpected parse errors
        return None, f"Failed to load bank: {exc}"


def _try_load_lab(path: Path) -> tuple[LabBank | None, str | None]:
    size_err = _check_file_size(path)
    if size_err:
        return None, size_err
    try:
        return load_lab(path), None
    except LabLoaderError as exc:
        return None, str(exc)
    except Exception as exc:  # noqa: BLE001
        return None, f"Failed to load lab: {exc}"


def _lab_limit_errors(lab: LabBank) -> str | None:
    n_dev = len(lab.topology.devices)
    if n_dev > MAX_DEVICES_PER_LAB:
        return f"Lab {lab.lab_id} exceeds device limit ({n_dev} > {MAX_DEVICES_PER_LAB})"
    n_tasks = len(lab.tasks)
    if n_tasks > MAX_TASKS_PER_LAB:
        return f"Lab {lab.lab_id} exceeds task limit ({n_tasks} > {MAX_TASKS_PER_LAB})"
    return None


def _load_pack_content_file(
    path: Path,
) -> tuple[str | None, ExamBank | None, LabBank | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001
        return None, None, None, f"YAML parse failed: {exc}"
    if not isinstance(raw, dict):
        return None, None, None, "YAML root must be a mapping"
    if "lab_id" in raw or ("tasks" in raw and "topology" in raw):
        lab, err = _try_load_lab(path)
        if err:
            return "lab", None, None, err
        return "lab", None, lab, None
    if "questions" in raw:
        bank, err = _try_load_bank(path)
        if err:
            return "bank", None, None, err
        return "bank", bank, None, None
    return None, None, None, "Unrecognized content (expected bank or lab YAML)"


def _validate_rel_path(rel: str) -> None:
    if not rel or not isinstance(rel, str):
        raise PackError("File path must be a non-empty string")
    if _URL_RE.match(rel):
        raise PackError(f"External URL references are not allowed: {rel}")
    if _ABS_PATH_RE.match(rel) or Path(rel).is_absolute():
        raise PackError(f"Absolute file paths are not allowed: {rel}")
    parts = Path(rel).parts
    if ".." in parts:
        raise PackError(f"Parent-directory references are not allowed: {rel}")
    if any(p.startswith("~") for p in parts):
        raise PackError(f"Home-directory references are not allowed: {rel}")


def _load_pack_manifest(path: Path, pack_dir: Path) -> dict[str, Any]:
    size_err = _check_file_size(path)
    if size_err:
        raise PackError(size_err)
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001
        raise PackError(f"Failed to parse pack.yaml: {exc}") from exc
    if not isinstance(raw, dict):
        raise PackError("pack.yaml root must be a mapping")

    forbidden = sorted(k for k in raw if k.lower() in _FORBIDDEN_MANIFEST_KEYS)
    if forbidden:
        raise PackError(
            "Executable hooks / scripts are not allowed in pack manifests: " + ", ".join(forbidden)
        )

    required = (
        "id",
        "name",
        "version",
        "schema_version",
        "provider",
        "license",
        "cert_tags",
        "min_app_version",
        "files",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise PackError(f"pack.yaml missing required fields: {', '.join(missing)}")

    pack_id = str(raw["id"]).strip()
    if not pack_id:
        raise PackError("pack id must be non-empty")
    if pack_id != pack_dir.name:
        raise PackError(f"pack id {pack_id!r} does not match directory name {pack_dir.name!r}")

    files_raw = raw["files"]
    if not isinstance(files_raw, list) or not files_raw:
        raise PackError("pack.yaml files must be a non-empty list")

    files: list[dict[str, str]] = []
    for item in files_raw:
        if not isinstance(item, dict):
            raise PackError("Each files entry must be a mapping with path and sha256")
        item_forbidden = sorted(k for k in item if k.lower() in _FORBIDDEN_MANIFEST_KEYS)
        if item_forbidden:
            raise PackError(
                "Executable hooks are not allowed on file entries: " + ", ".join(item_forbidden)
            )
        if "path" not in item or "sha256" not in item:
            raise PackError("Each files entry requires path and sha256")
        rel = str(item["path"]).replace("\\", "/")
        _validate_rel_path(rel)
        digest = str(item["sha256"]).strip()
        if not _SHA256_RE.match(digest):
            raise PackError(f"Invalid SHA-256 for {rel}: {digest!r}")
        files.append({"path": rel, "sha256": digest.lower()})

    cert_tags = raw["cert_tags"]
    if not isinstance(cert_tags, list):
        raise PackError("cert_tags must be a list")

    return {
        "id": pack_id,
        "name": str(raw["name"]),
        "version": str(raw["version"]),
        "schema_version": int(raw["schema_version"]),
        "provider": str(raw["provider"]),
        "license": str(raw["license"]),
        "cert_tags": [str(t) for t in cert_tags],
        "min_app_version": str(raw["min_app_version"]),
        "files": files,
    }


def _parse_version(value: str) -> tuple[int, ...]:
    core = value.strip().split("+", 1)[0].split("-", 1)[0]
    parts: list[int] = []
    for piece in core.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def _version_satisfies(minimum: str, current: str) -> bool:
    """Return True when ``current`` is greater than or equal to ``minimum``."""
    a = _parse_version(minimum)
    b = _parse_version(current)
    # Pad to equal length
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    return b >= a
