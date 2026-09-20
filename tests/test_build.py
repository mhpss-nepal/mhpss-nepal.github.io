#!/usr/bin/env python3
"""End-to-end tests for the fresh-path artifact generator."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fixture_repo import BUILD_SCRIPT, REPOSITORY_ROOT, create_repository, run_build


class BuildTests(unittest.TestCase):
    def test_build_maps_exactly_120_application_files_to_stable_addresses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            output = root / "artifact"

            completed = run_build(sources, output, commit=commit)

            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            files = sorted(path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file())
            self.assertEqual(len(files), 120)
            self.assertIn("index.html", files)
            self.assertIn("form/index.html", files)
            self.assertIn("hub/index.html", files)

    def test_two_fresh_builds_have_identical_json_manifests_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            manifests: list[dict[str, object]] = []
            for name in ("first", "second"):
                output = root / name
                built = run_build(sources, output, commit=commit)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
                shown = subprocess.run(
                    [sys.executable, str(BUILD_SCRIPT), "--manifest", str(output)],
                    cwd=REPOSITORY_ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(shown.returncode, 0, shown.stdout + shown.stderr)
                manifest = json.loads(shown.stdout)
                self.assertEqual(manifest["schema"], 2)
                self.assertEqual(manifest["total_files"], 120)
                self.assertIsInstance(manifest["files"], list)
                self.assertIsInstance(manifest["directories"], list)
                self.assertEqual(manifest["total_directories"], len(manifest["directories"]))
                self.assertIn(
                    {"path": "form", "mode": "0755", "mtime_ns": 946684800 * 1_000_000_000},
                    manifest["directories"],
                )
                manifests.append(manifest)
                for path in (output, *output.rglob("*")):
                    expected = 0o755 if path.is_dir() else 0o644
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), expected)
                    self.assertEqual(path.stat().st_mtime_ns, 946684800 * 1_000_000_000)
            self.assertEqual(manifests[0], manifests[1])


if __name__ == "__main__":
    unittest.main()
