#!/usr/bin/env python3
"""Verified landing of one finished frontend commit into the monorepo.

The monorepo does not consume the frontend branches live: ``apps/public``,
``apps/form`` and ``apps/hub`` are snapshots of separate repositories. This tool
turns "install the finished branch" into one explicit, auditable, fail-closed
step. It:

1. accepts only an exact full commit SHA, a real source repository, and a target
   application (``public`` | ``form`` | ``hub``); it refuses branch names, short
   or unresolved revisions, dirty source trees, and a dirty monorepo;
2. verifies the source commit is present and records provenance (repository,
   full commit SHA, timestamp, author) that can re-derive the import;
3. imports the source-controlled file set only, applying the builder's own
   classification, collision, exclusion and secret policy, and failing closed on
   anything unclassified;
4. proves byte-for-byte parity (path, length, SHA-256) between the imported tree
   and the source commit, and reports added / removed / changed paths against the
   previous monorepo snapshot so a silently dropped file cannot pass;
5. keeps repository metadata (``.git``, gitlinks, non-regular modes) out while
   recording the exact command that re-derives the import;
6. refuses to introduce a *new* cross-application runtime dependency (for example
   Form loading ``../hub/assets/``) unless an explicit override is acknowledged
   and recorded in the runbook;
7. never pushes, merges, deploys, or touches production, and never runs a
   remote-operation Git command; it only writes local files. Committing and
   building the landed tree is a separate, reviewed step in ``docs/LANDING.md``.

Dry-run is the default. ``--apply`` mutates the monorepo working tree only.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))

import layout  # noqa: E402
from layout import (  # noqa: E402
    APP_DESTINATIONS,
    APPLICATION_PATH_MANIFEST,
    MAX_FILES,
    MAX_FILE_BYTES,
    MAX_OBJECT_BYTES,
    canonical_path_key,
    forbidden_content_reason,
    parse_structured_data,
    validate_path_component,
)

SCHEMA = 1
PROVENANCE_PATH = "provenance/frontend-sources.json"
GIT_TIMEOUT_SECONDS = 60
MAX_METADATA_BYTES = 64 * 1024

# Applications whose files land in this monorepo and the exact upstream identity
# each one must present. A source repository whose identity does not match the
# target application is refused, so work cannot be landed against the wrong app.
EXPECTED_ORIGINS = {
    "public": "git@github.com:mhpss-nepal/mhpss-nepal.github.io.git",
    "form": "git@github.com:mhpss-nepal/form.git",
    "hub": "git@github.com:mhpss-nepal/hub.git",
}

# Matches a relative reference to a sibling application, e.g. ``../hub/assets/``.
CROSS_APP_REFERENCE = re.compile(r"\.\./(public|form|hub)(/[A-Za-z0-9._~%+-]+)+")
_CROSS_APP_SCAN_SUFFIXES = {
    ".html",
    ".htm",
    ".css",
    ".js",
    ".mjs",
    ".json",
    ".webmanifest",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".conf",
    ".sha",
    ".py",
}

# A landing may only import file kinds this project already classifies as
# application assets. Anything else is unclassified and fails closed; adding a
# new kind is a deliberate policy change, not an accident of a landing.
_CLASSIFIED_SUFFIXES = {
    ".html", ".htm", ".css", ".js", ".mjs", ".json", ".webmanifest",
    ".md", ".txt", ".conf", ".sha", ".py", ".yaml", ".yml", ".xml",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".map",
}
_CLASSIFIED_NAMES = {".gitignore", ".nojekyll"}

_FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")


class LandingError(ValueError):
    """A refused landing. The message is shown to the operator."""


@dataclass(frozen=True)
class LandingFile:
    """One source-controlled file to be imported."""

    path: str  # path relative to the source commit root
    data: bytes


@dataclass(frozen=True)
class SourceProvenance:
    repository: str
    commit: str
    timestamp: str
    author: str


def _sanitized_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment["GIT_NO_LAZY_FETCH"] = "1"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _git(repository: Path, git_dir: Path, *arguments: str, stdout_limit: int = MAX_OBJECT_BYTES + 4096) -> bytes:
    command = [
        "git",
        "--no-replace-objects",
        f"--git-dir={git_dir}",
        f"--work-tree={repository}",
        *arguments,
    ]
    return_code, stdout, stderr = layout._bounded_process(
        command,
        stdout_limit=stdout_limit,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    if return_code:
        diagnostic = stderr.decode("utf-8", "replace").strip()
        raise LandingError(f"git {' '.join(arguments)} failed: {diagnostic or 'unknown git error'}")
    return stdout


def _resolve_git_dir(repository: Path, label: str) -> Path:
    dot_git = repository / ".git"
    try:
        metadata = os.lstat(dot_git)
    except FileNotFoundError as error:
        raise LandingError(f"{label} is not a Git repository: {repository}") from error
    if stat.S_ISDIR(metadata.st_mode):
        return dot_git
    if stat.S_ISREG(metadata.st_mode):
        text = dot_git.read_text(encoding="utf-8", errors="strict").strip()
        if not text.startswith("gitdir: "):
            raise LandingError(f"invalid Git worktree metadata for {label}: {dot_git}")
        candidate = Path(text[8:])
        return candidate if candidate.is_absolute() else (repository / candidate).resolve()
    raise LandingError(f"repository metadata for {label} is not a file or directory: {dot_git}")


def _assert_clean(repository: Path, git_dir: Path, label: str) -> None:
    status = _git(repository, git_dir, "status", "--porcelain", "--untracked-files=normal", stdout_limit=MAX_METADATA_BYTES)
    if status.strip():
        first = status.decode("utf-8", "replace").splitlines()[0]
        raise LandingError(f"{label} worktree is dirty; refusing to land ({first})")
    for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG"):
        if (git_dir / marker).exists():
            raise LandingError(f"{label} repository has an in-progress git operation ({marker})")


def normalize_repository_url(url: str) -> str:
    """Reduce a git remote URL to a comparable ``host/path`` identity."""
    text = url.strip()
    text = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", "", text)  # scheme
    text = text.split("@", 1)[1] if "@" in text.split("/", 1)[0] else text
    text = text.replace(":", "/", 1) if re.match(r"[^/]+:[^/]", text) else text
    text = text.rstrip("/")
    if text.lower().endswith(".git"):
        text = text[:-4]
    return text.casefold()


def _verify_identity(repository: Path, git_dir: Path, expected: str) -> str:
    raw = _git(repository, git_dir, "remote", "get-url", "origin", stdout_limit=MAX_METADATA_BYTES)
    actual = raw.decode("utf-8", "strict").strip()
    if normalize_repository_url(actual) != normalize_repository_url(expected):
        raise LandingError(
            f"source repository identity {actual!r} does not match the expected {expected!r} for this target application"
        )
    return actual


def _read_commit_metadata(repository: Path, git_dir: Path, commit: str) -> tuple[str, str]:
    raw = _git(repository, git_dir, "show", "-s", "--format=%aI%n%an <%ae>", commit, stdout_limit=MAX_METADATA_BYTES)
    lines = raw.decode("utf-8", "replace").splitlines()
    if len(lines) < 2:
        raise LandingError(f"could not read provenance for commit {commit}")
    return lines[0].strip(), lines[1].strip()


def _list_commit_tree(repository: Path, git_dir: Path, commit: str) -> tuple[tuple[LandingFile, ...], tuple[str, ...]]:
    """Return every regular file in one commit, rejecting metadata and gitlinks."""
    raw = _git(repository, git_dir, "ls-tree", "-r", "-z", "--full-tree", commit, stdout_limit=MAX_OBJECT_BYTES * 4)
    files: list[LandingFile] = []
    directories: list[str] = []
    total_bytes = 0
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            header, name = record.split(b"\t", 1)
            mode, object_type, oid = header.decode("ascii", "strict").split(" ")
            path = name.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError) as error:
            raise LandingError("source commit contains a malformed tree entry") from error
        if object_type == "tree" or mode == "40000":
            directories.append(path)
            continue
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise LandingError(f"source commit contains a non-regular entry (gitlink or special mode): {path} ({mode})")
        if "/" not in path and path == ".git":
            raise LandingError("source commit contains repository metadata")
        data = layout._read_object(repository, git_dir, oid, "blob")
        if len(data) > MAX_FILE_BYTES:
            raise LandingError(f"per-file byte limit exceeded in source commit: {path}")
        total_bytes += len(data)
        if total_bytes > layout.MAX_TOTAL_BYTES:
            raise LandingError("total byte limit exceeded for the source commit")
        files.append(LandingFile(path=path, data=data))
    return tuple(files), tuple(directories)


def resolve_source(
    repository: Path,
    commit: str,
    expected_origin: str,
) -> tuple[SourceProvenance, tuple[LandingFile, ...]]:
    """Resolve and verify one exact source commit; refuse anything unpinned."""
    if not _FULL_SHA.fullmatch(commit):
        raise LandingError(
            f"--commit must be a full commit SHA of 40 hex characters, not a branch, tag, or short ref: {commit!r}"
        )
    repository = Path(os.path.abspath(os.fspath(repository)))
    git_dir = _resolve_git_dir(repository, "source repository")
    _assert_clean(repository, git_dir, "source")
    actual_origin = _verify_identity(repository, git_dir, expected_origin)
    try:
        resolved = _git(
            repository, git_dir, "rev-parse", "--verify", "--end-of-options", f"{commit}^{{commit}}", stdout_limit=256
        ).decode("ascii", "strict").strip()
    except LandingError as error:
        raise LandingError(f"source commit does not exist or is not reachable in the source repository: {commit}") from error
    if not _FULL_SHA.fullmatch(resolved) or resolved != commit:
        raise LandingError(f"source commit does not exist or is not the requested SHA: {commit}")
    timestamp, author = _read_commit_metadata(repository, git_dir, commit)
    files, _ = _list_commit_tree(repository, git_dir, commit)
    return SourceProvenance(actual_origin, resolved, timestamp, author), files


# --------------------------------------------------------------------------- #
# Monorepo classification state
# --------------------------------------------------------------------------- #


def load_manifest(monorepo: Path) -> tuple[tuple[str, ...], frozenset[str]]:
    manifest_path = monorepo / APPLICATION_PATH_MANIFEST
    try:
        raw = layout._read_small_regular(manifest_path, 512 * 1024, "application path manifest")
    except FileNotFoundError as error:
        raise LandingError(f"missing application path manifest: {manifest_path}") from error
    value = parse_structured_data(APPLICATION_PATH_MANIFEST, raw)
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise LandingError(f"unsupported application path manifest schema: {manifest_path}")
    paths = value.get("paths")
    if not isinstance(paths, list) or not paths:
        raise LandingError(f"application path manifest has no paths: {manifest_path}")
    registry = layout._PathRegistry()
    ordered: list[str] = []
    for path in paths:
        if not isinstance(path, str):
            raise LandingError(f"application path manifest contains a non-string path: {manifest_path}")
        parts = path.split("/")
        if len(parts) < 3 or parts[0] != "apps" or parts[1] not in APP_DESTINATIONS or not parts[2]:
            raise LandingError(f"application path manifest contains an unclassified path: {path}")
        layout._validate_git_path(path)
        registry.add(path, kind="manifest path")
        ordered.append(path)
    if len(ordered) > MAX_FILES:
        raise LandingError("application path manifest exceeds the file budget")
    return tuple(ordered), frozenset(ordered)


def read_app_tree(monorepo: Path, target: str, manifest: frozenset[str]) -> tuple[dict[str, bytes], list[str]]:
    """Read the classified monorepo snapshot for one application.

    Only paths in the reviewed manifest are part of the snapshot, so untracked or
    ignored working-tree debris (for example generated ``__pycache__``) is neither
    compared nor removed. Unclassified files that *are* present under the
    application are returned separately so the report can name them; the builder
    reads the committed tree, where such files would already fail closed.
    """
    root = monorepo / "apps" / target
    if not root.is_dir():
        raise LandingError(f"target application directory is missing: {root}")
    prefix = f"apps/{target}/"
    classified: dict[str, bytes] = {}
    for path in sorted(manifest):
        if not path.startswith(prefix):
            continue
        relative = path[len(prefix):]
        candidate = root / relative
        try:
            data = layout._read_small_regular(candidate, MAX_FILE_BYTES, f"monorepo snapshot file {relative}")
        except FileNotFoundError as error:
            raise LandingError(f"classified path is missing from the monorepo: {path}") from error
        classified[relative] = data
    present = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    unclassified = sorted(present - set(classified))
    return classified, unclassified


def collect_cross_app_references(files: dict[str, bytes]) -> set[str]:
    references: set[str] = set()
    for path, data in files.items():
        if PurePosixPath(path).suffix.casefold() not in _CROSS_APP_SCAN_SUFFIXES:
            continue
        text = data.decode("utf-8", "replace")
        for match in CROSS_APP_REFERENCE.finditer(text):
            references.add(match.group(0).split("?")[0].split("#")[0])
    return references


# --------------------------------------------------------------------------- #
# Classification and parity
# --------------------------------------------------------------------------- #


def classify(
    files: tuple[LandingFile, ...],
    target: str,
    manifest: frozenset[str],
) -> tuple[tuple[tuple[str, bytes], ...], tuple[str, ...]]:
    """Map source files to monorepo paths, failing closed on anything unsafe."""
    registry = layout._PathRegistry()
    imported: list[tuple[str, bytes]] = []
    new_paths: list[str] = []
    for entry in files:
        if entry.path == ".git" or any(part.casefold() == ".git" for part in entry.path.split("/")):
            raise LandingError(f"source file set contains repository metadata: {entry.path}")
        name = PurePosixPath(entry.path).name
        suffix = PurePosixPath(entry.path).suffix.casefold()
        if name not in _CLASSIFIED_NAMES and suffix not in _CLASSIFIED_SUFFIXES:
            raise LandingError(
                f"unclassified source file kind refused by the application-asset policy: {entry.path}"
            )
        destination = f"apps/{target}/{entry.path}"
        layout._validate_git_path(destination)
        registry.add(destination, kind="imported file")
        if layout._forbidden_path(destination):
            raise LandingError(f"excluded content refused by policy: {destination}")
        reason = forbidden_content_reason(destination, entry.data)
        if reason is not None:
            raise LandingError(f"forbidden committed source contains {reason}: {destination}")
        parse_structured_data(destination, entry.data)
        if destination not in manifest:
            new_paths.append(destination)
        imported.append((destination, entry.data))
    if not imported:
        raise LandingError("source commit has no files to import")
    return tuple(imported), tuple(sorted(new_paths))


def verify_tree_parity(
    expected: tuple[LandingFile, ...],
    directory: Path,
    allowed_extra: frozenset[str] = frozenset(),
) -> list[str]:
    """Assert a materialized directory matches the expected path/length/SHA-256 set.

    ``allowed_extra`` names working-tree debris that is deliberately not part of
    the committed import (for example ignored ``__pycache__``); it is reported but
    not treated as a parity defect. Untracked files never enter the committed tree
    the builder reads.
    """
    expected_map = {entry.path: entry.data for entry in expected}
    actual_map = {
        path.relative_to(directory).as_posix(): path
        for path in directory.rglob("*")
        if path.is_file()
    }
    for path in sorted(set(expected_map) - set(actual_map)):
        raise LandingError(f"missing imported file: {path}")
    extra = sorted(set(actual_map) - set(expected_map))
    for path in extra:
        if path not in allowed_extra:
            raise LandingError(f"unexpected imported file: {path}")
    for path in sorted(expected_map):
        actual = actual_map[path].read_bytes()
        if len(actual) != len(expected_map[path]) or hashlib.sha256(actual).digest() != hashlib.sha256(expected_map[path]).digest():
            raise LandingError(f"imported file does not match the source commit: {path}")
    return extra


def _write_file(root: Path, relative: str, data: bytes) -> None:
    parts = relative.split("/")
    for component in parts:
        validate_path_component(component, label="imported path")
    parent = root
    for component in parts[:-1]:
        parent = parent / component
        parent.mkdir(mode=0o755, exist_ok=True)
    destination = parent / parts[-1]
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_CLOEXEC | os.O_NOFOLLOW, 0o644)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("write made no progress")
            view = view[written:]
        os.fchmod(descriptor, 0o644)
    finally:
        os.close(descriptor)


def _prune_empty_directories(target_root: Path) -> None:
    for path in sorted((p for p in target_root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def apply_landing(
    monorepo: Path,
    target: str,
    imported: tuple[tuple[str, bytes], ...],
    previous_relative: frozenset[str],
    allowed_extra: frozenset[str] = frozenset(),
) -> dict[str, list[str]]:
    """Write the imported tree, remove vanished paths, then re-verify parity."""
    target_root = monorepo / "apps" / target
    prefix = f"apps/{target}/"
    new_relative = {destination[len(prefix):] for destination, _ in imported}

    for destination, data in sorted(imported):
        _write_file(target_root, destination[len(prefix):], data)

    removed = sorted(set(previous_relative) - new_relative)
    for relative in removed:
        candidate = target_root / relative
        if candidate.is_file() and not candidate.is_symlink():
            candidate.unlink()
    _prune_empty_directories(target_root)

    expected = tuple(LandingFile(path=destination[len(prefix):], data=data) for destination, data in imported)
    verify_tree_parity(expected, target_root, allowed_extra=allowed_extra)
    return {"removed_relative": removed}


def update_manifest(
    monorepo: Path,
    ordered: tuple[str, ...],
    target: str,
    candidate_relative: "dict[str, bytes] | set[str]",
) -> tuple[str, ...]:
    """Rewrite the manifest: replace the target app's paths with the landed set."""
    prefix = f"apps/{target}/"
    others = [path for path in ordered if not path.startswith(prefix)]
    landed = sorted({f"{prefix}{path}" for path in candidate_relative})
    combined = sorted(set(others) | set(landed), key=canonical_path_key)
    registry = layout._PathRegistry()
    for path in combined:
        layout._validate_git_path(path)
        registry.add(path, kind="manifest path")
    if not combined:
        raise LandingError("application path manifest would become empty")
    if len(combined) > MAX_FILES:
        raise LandingError("application path manifest would exceed the file budget")
    value = {"paths": combined, "schema": SCHEMA}
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    (monorepo / APPLICATION_PATH_MANIFEST).write_text(payload, encoding="utf-8")
    return tuple(combined)


def load_provenance(monorepo: Path, target: str) -> dict[str, object]:
    path = monorepo / PROVENANCE_PATH
    try:
        raw = layout._read_small_regular(path, 512 * 1024, "provenance file")
    except FileNotFoundError as error:
        raise LandingError(f"missing provenance file: {path}") from error
    value = parse_structured_data(PROVENANCE_PATH, raw)
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise LandingError(f"unsupported provenance schema: {path}")
    applications = value.get("applications")
    if not isinstance(applications, dict) or target not in applications:
        raise LandingError(f"provenance is missing the {target} application record: {path}")
    return applications[target]


def update_provenance(
    monorepo: Path,
    target: str,
    provenance: SourceProvenance,
    command: str,
) -> dict[str, dict[str, str]]:
    path = monorepo / PROVENANCE_PATH
    try:
        raw = layout._read_small_regular(path, 512 * 1024, "provenance file")
        value = parse_structured_data(PROVENANCE_PATH, raw)
        if not isinstance(value, dict) or not isinstance(value.get("applications"), dict):
            raise LandingError(f"unsupported provenance schema: {path}")
    except FileNotFoundError:
        value = {"applications": {}, "schema": SCHEMA}
    applications = value["applications"]
    applications[target] = {
        "author": provenance.author,
        "commit": provenance.commit,
        "commit_timestamp": provenance.timestamp,
        "rederive_command": command,
        "repository": provenance.repository,
        "repository_key": normalize_repository_url(provenance.repository),
    }
    value["schema"] = SCHEMA
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return applications


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--monorepo", required=True, type=Path, help="monorepo worktree to land into")
    parser.add_argument("--source-repo", required=True, type=Path, help="source repository worktree")
    parser.add_argument("--commit", required=True, help="exact full 40-character commit SHA")
    parser.add_argument("--target-app", required=True, choices=sorted(APP_DESTINATIONS), help="application to land")
    parser.add_argument("--apply", action="store_true", help="write the landing (default is a dry run)")
    parser.add_argument(
        "--acknowledge-cross-app-dependency",
        default=None,
        help="explicit override text recorded when a landing adds a cross-application runtime dependency",
    )
    return parser.parse_args(argv)


def land(arguments: argparse.Namespace) -> dict[str, object]:
    monorepo = Path(os.path.abspath(os.fspath(arguments.monorepo)))
    monorepo_git_dir = _resolve_git_dir(monorepo, "monorepo")
    _assert_clean(monorepo, monorepo_git_dir, "monorepo")

    target = arguments.target_app
    expected_origin = EXPECTED_ORIGINS[target]
    provenance, files = resolve_source(arguments.source_repo, arguments.commit, expected_origin)

    ordered, manifest = load_manifest(monorepo)
    previous, previously_unclassified = read_app_tree(monorepo, target, manifest)
    prefix = f"apps/{target}/"
    previous_paths = frozenset(f"{prefix}{path}" for path in previous)
    previous_relative = frozenset(previous)

    imported, new_paths = classify(files, target, manifest)
    candidate_map = {destination: data for destination, data in imported}
    candidate_relative = {destination[len(prefix):]: data for destination, data in candidate_map.items()}

    changed = sorted(
        path
        for path in previous_relative & set(candidate_relative)
        if candidate_relative[path] != previous[path]
    )
    added = sorted(set(candidate_relative) - previous_relative)
    removed = sorted(previous_relative - set(candidate_relative))

    # Cross-application runtime dependency contract.
    candidate_refs = collect_cross_app_references(candidate_relative)
    previous_refs = collect_cross_app_references(previous)
    added_refs = sorted(candidate_refs - previous_refs)
    override = arguments.acknowledge_cross_app_dependency
    if added_refs and not (override and override.strip()):
        raise LandingError(
            "cross-application runtime dependency would be added "
            f"({', '.join(added_refs)}); pass --acknowledge-cross-app-dependency with a recorded override"
        )

    command = (
        f"python3 scripts/land.py --monorepo . --source-repo <clean source worktree> "
        f"--commit {provenance.commit} --target-app {target} --apply"
    )

    report: dict[str, object] = {
        "schema": SCHEMA,
        "mode": "apply" if arguments.apply else "dry-run",
        "target_app": target,
        "source": {
            "commit": provenance.commit,
            "commit_timestamp": provenance.timestamp,
            "author": provenance.author,
            "repository": provenance.repository,
        },
        "parity_verified": True,
        "files_imported": len(imported),
        "new_classified_paths": list(new_paths),
        "previous": {"file_count": len(previous_paths)},
        "unclassified_present_before": previously_unclassified,
        "candidate": {
            "file_count": len(imported),
            "total_bytes": sum(len(data) for _, data in imported),
            "files": [
                {
                    "path": destination[len(f"apps/{target}/"):],
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                for destination, data in sorted(imported)
            ],
        },
        "changes": {"added": added, "changed": changed, "removed": removed},
        "cross_application_dependency": {
            "acknowledged": bool(added_refs and override and override.strip()),
            "previous_references": sorted(previous_refs),
            "candidate_references": sorted(candidate_refs),
            "added_references": added_refs,
            "override": override if added_refs else None,
        },
        "repository_metadata_excluded": True,
        "rederive_command": command,
        "applied": False,
    }

    if arguments.apply:
        apply_landing(
            monorepo,
            target,
            imported,
            previous_relative,
            allowed_extra=frozenset(previously_unclassified),
        )
        update_manifest(monorepo, ordered, target, candidate_relative)
        update_provenance(monorepo, target, provenance, command)
        report["applied"] = True
        report["provenance"] = load_provenance(monorepo, target)
    return report


def main(argv: list[str] | None = None) -> int:
    arguments = _parse_args(argv)
    try:
        report = land(arguments)
    except (LandingError, OSError, ValueError) as error:
        if isinstance(error, OSError) and error.errno == errno.ELOOP:
            print("land failed: path substitution or symlink was refused", file=sys.stderr)
        else:
            print(f"land failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
