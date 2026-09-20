#!/usr/bin/env python3
"""Git fixture helpers for artifact-generator tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPOSITORY_ROOT / "scripts" / "build.py"
VALIDATE_SCRIPT = REPOSITORY_ROOT / "scripts" / "validate.py"


def _git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=check,
        capture_output=True,
        text=True,
    )


TRACKED_APPLICATION_PATHS = tuple(
    _git(REPOSITORY_ROOT, "ls-tree", "-r", "--name-only", "HEAD", "--", "apps").stdout.splitlines()
)
# The classified path allowlist is committed data (``config/application-paths.json``),
# not a Python literal, so a landing can add paths in a reviewable manifest change.
MANIFEST_PATHS = tuple(
    json.loads((REPOSITORY_ROOT / "config" / "application-paths.json").read_text(encoding="utf-8"))["paths"]
)


def write_path_manifest(repository: Path, paths: tuple[str, ...] = TRACKED_APPLICATION_PATHS) -> None:
    manifest = repository / "config" / "application-paths.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({"paths": sorted(paths), "schema": 1}, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def fixture_bytes(path: str, label: str = "fixture") -> bytes:
    if path == "apps/hub/data/demo.json":
        return b'{"synthetic":true,"records":[]}\n'
    if path == "apps/hub/data/demo.js":
        return b'/* Synthetic demonstration data; never operational data. */\nwindow.DEMO=[];\n'
    if path == "apps/form/manifest.webmanifest":
        return b'{"name":"Fixture","start_url":"./","icons":[]}\n'
    if path == "apps/hub/data/README.md":
        return b"# Synthetic demonstration data\n\n`demo.json` and `demo.js` are source-controlled synthetic examples, not real data.\n"
    return f"{label}: {path}\n".encode()


def create_repository(root: Path, label: str = "fixture") -> tuple[Path, Path, str]:
    repository = root / "repository"
    repository.mkdir(parents=True)
    _git(repository, "init", "-q")
    for relative in TRACKED_APPLICATION_PATHS:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fixture_bytes(relative, label))
    write_path_manifest(repository)
    provenance = repository / "provenance" / "frontend-sources.json"
    provenance.parent.mkdir(parents=True, exist_ok=True)
    provenance.write_text(
        json.dumps({"applications": {}, "schema": 1}, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    commit = commit_all(repository, label)
    return repository, repository / "apps", commit


def commit_all(repository: Path, message: str = "fixture") -> str:
    _git(repository, "add", "-A", "-f")
    _git(
        repository,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )
    return _git(repository, "rev-parse", "HEAD").stdout.strip()


def run_script(
    script: Path,
    sources: Path,
    output: Path,
    *,
    commit: str | None = None,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(script),
        "--source-root",
        str(sources),
        "--output",
        str(output),
    ]
    if commit is not None:
        command.extend(["--commit", commit])
    return subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )


def run_build(
    sources: Path,
    output: Path,
    *,
    commit: str | None = None,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return run_script(BUILD_SCRIPT, sources, output, commit=commit, environment=environment)


def run_validate(
    sources: Path,
    output: Path,
    *,
    commit: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return run_script(VALIDATE_SCRIPT, sources, output, commit=commit)


def clean_environment(**updates: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(updates)
    return environment
