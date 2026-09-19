#!/usr/bin/env python3
"""Validate a bounded artifact against one independently verified Git commit."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath

from layout import NORMALIZED_MTIME, inspect_source, read_output_tree

REQUIRED_OUTPUT_PATHS = {"index.html", "form/index.html", "hub/index.html"}
EXPECTED_MTIME_NS = NORMALIZED_MTIME * 1_000_000_000


def validate(source_root: Path, output: Path, revision: str = "HEAD") -> list[str]:
    try:
        layout = inspect_source(source_root, revision)
    except (OSError, ValueError) as error:
        return [str(error)]
    try:
        _, actual_files, actual_directories = read_output_tree(output)
    except (OSError, ValueError) as error:
        return [str(error)]

    expected_files = {entry.destination.as_posix(): entry.data for entry in layout.entries}
    expected_directories = {"."}
    for entry in layout.entries:
        current = entry.destination.parent
        while current not in {PurePosixPath("."), PurePosixPath("")}:
            expected_directories.add(current.as_posix())
            current = current.parent

    actual_file_map = {entry.path: entry for entry in actual_files}
    actual_directory_map = {entry.path: entry for entry in actual_directories}
    errors: list[str] = []

    for required in sorted(REQUIRED_OUTPUT_PATHS):
        if required not in actual_file_map:
            errors.append(f"missing required output path: {required}")
    for path in sorted(set(expected_files) - set(actual_file_map)):
        errors.append(f"missing output file: {path}")
    for path in sorted(set(actual_file_map) - set(expected_files)):
        errors.append(f"unexpected output file: {path}")
    for path in sorted(expected_directories - set(actual_directory_map)):
        errors.append(f"missing output directory: {path}")
    for path in sorted(set(actual_directory_map) - expected_directories):
        errors.append(f"unexpected output directory: {path}")

    for path in sorted(set(expected_files) & set(actual_file_map)):
        actual = actual_file_map[path]
        if actual.data != expected_files[path]:
            errors.append(f"output differs from committed source: {path}")
        if actual.mode != 0o644 or actual.mtime_ns != EXPECTED_MTIME_NS:
            errors.append(f"invalid output metadata: {path}")
    for path in sorted(expected_directories & set(actual_directory_map)):
        actual = actual_directory_map[path]
        if actual.mode != 0o755 or actual.mtime_ns != EXPECTED_MTIME_NS:
            errors.append(f"invalid output metadata: {path}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("apps"))
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--commit", default="HEAD", help="committed Git revision to validate")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    errors = validate(arguments.source_root, arguments.output, arguments.commit)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
