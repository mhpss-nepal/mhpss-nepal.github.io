#!/usr/bin/env python3
"""Generate a deterministic artifact once at a fresh, absent output path."""

from __future__ import annotations

import argparse
import errno
import os
import stat
from pathlib import Path, PurePosixPath

from layout import (
    NORMALIZED_MTIME,
    SourceLayout,
    inspect_source,
    json_manifest,
    validate_path_component,
)

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
_FILE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW


def _open_parent(output: Path) -> tuple[int, str, Path]:
    """Open the output parent link-free and retain its identity by descriptor."""
    absolute = output if output.is_absolute() else Path.cwd() / output
    if absolute.name in {"", ".", ".."}:
        raise ValueError(f"output path must name a fresh directory: {output}")
    validate_path_component(absolute.name, label="output path")
    parent = absolute.parent
    descriptor = os.open(parent.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in parent.parts[1:]:
            if component in {"", "."}:
                continue
            if component == ".." or component.casefold() == ".git":
                raise ValueError(f"unsafe output parent component: {component!r}")
            next_descriptor = os.open(component, _DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor, absolute.name, Path(os.path.abspath(os.fspath(absolute)))
    except BaseException:
        os.close(descriptor)
        raise


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("write made no progress")
        view = view[written:]


def _ensure_directory(root_descriptor: int, destination: PurePosixPath) -> int:
    """Open or create only artifact-owned directories beneath the fresh root."""
    descriptor = os.dup(root_descriptor)
    try:
        for component in destination.parts:
            if component in {"", "."}:
                continue
            try:
                os.mkdir(component, mode=0o755, dir_fd=descriptor)
            except FileExistsError:
                pass
            next_descriptor = os.open(component, _DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _create_file(root_descriptor: int, destination: PurePosixPath, data: bytes) -> None:
    parent_descriptor = _ensure_directory(root_descriptor, destination.parent)
    try:
        descriptor = os.open(destination.name, _FILE_FLAGS, 0o644, dir_fd=parent_descriptor)
        try:
            _write_all(descriptor, data)
            os.fchmod(descriptor, 0o644)
            os.utime(descriptor, (NORMALIZED_MTIME, NORMALIZED_MTIME))
        finally:
            os.close(descriptor)
    finally:
        os.close(parent_descriptor)


def _normalize_directories(root_descriptor: int, directories: set[PurePosixPath]) -> None:
    for relative in sorted(directories, key=lambda path: (len(path.parts), path.as_posix()), reverse=True):
        descriptor = _ensure_directory(root_descriptor, relative)
        try:
            os.fchmod(descriptor, 0o755)
            os.utime(descriptor, (NORMALIZED_MTIME, NORMALIZED_MTIME))
        finally:
            os.close(descriptor)
    os.fchmod(root_descriptor, 0o755)
    os.utime(root_descriptor, (NORMALIZED_MTIME, NORMALIZED_MTIME))


def build(source_root: Path, output: Path, revision: str = "HEAD") -> SourceLayout:
    """Build from verified objects, refusing every pre-existing output path."""
    # First pass: confirm the output path is fresh, then close the parent again so
    # the whole committed source is scanned BEFORE any output exists. A rejected
    # source therefore leaves the filesystem untouched and creates nothing to clean.
    parent_descriptor, output_name, output_path = _open_parent(output)
    try:
        try:
            os.stat(output_name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError(f"output path already exists; choose a fresh path: {output_path}")
    finally:
        os.close(parent_descriptor)

    layout = inspect_source(source_root, revision)
    source_path = layout.root
    if output_path == source_path or output_path.is_relative_to(source_path) or source_path.is_relative_to(output_path):
        raise ValueError(f"output and source root must not overlap: {output_path}")

    # Second pass: re-open the parent link-free, re-confirm the path is still
    # absent, and create the output exactly once beneath the acquired descriptor.
    parent_descriptor, output_name, output_path = _open_parent(output)
    try:
        try:
            os.mkdir(output_name, mode=0o700, dir_fd=parent_descriptor)
        except FileExistsError as error:
            raise ValueError(f"output path already exists; choose a fresh path: {output_path}") from error
        created = os.stat(output_name, dir_fd=parent_descriptor, follow_symlinks=False)
        root_descriptor = os.open(output_name, _DIRECTORY_FLAGS, dir_fd=parent_descriptor)
        opened = os.fstat(root_descriptor)
        if (created.st_dev, created.st_ino) != (opened.st_dev, opened.st_ino):
            os.close(root_descriptor)
            raise ValueError("fresh output directory identity changed before acquisition")
    finally:
        os.close(parent_descriptor)

    # Once created, this directory is intentionally left in place on failure.
    # There is no recursive cleanup and no operation on any pre-existing output.
    try:
        directories: set[PurePosixPath] = {PurePosixPath(".")}
        for entry in layout.entries:
            current = entry.destination.parent
            while current not in {PurePosixPath("."), PurePosixPath("")}:
                directories.add(current)
                current = current.parent
            _create_file(root_descriptor, entry.destination, entry.data)
        _normalize_directories(root_descriptor, directories)
    finally:
        os.close(root_descriptor)
    return layout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("apps"))
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--commit", default="HEAD", help="committed Git revision to build")
    parser.add_argument("--manifest", type=Path, help="print a bounded JSON manifest for an existing output")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    try:
        if arguments.manifest is not None:
            print(json_manifest(arguments.manifest), end="")
        else:
            build(arguments.source_root, arguments.output, arguments.commit)
    except (OSError, ValueError) as error:
        if isinstance(error, OSError) and error.errno == errno.ELOOP:
            print("build failed: path substitution or symlink was refused")
        else:
            print(f"build failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
