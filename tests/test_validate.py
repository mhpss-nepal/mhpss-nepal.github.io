#!/usr/bin/env python3
"""Validation tests for exact generated artifacts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fixture_repo import create_repository, run_build, run_validate


class ValidationTests(unittest.TestCase):
    def test_validation_accepts_an_exact_fresh_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            output = root / "artifact"
            self.assertEqual(run_build(sources, output, commit=commit).returncode, 0)

            completed = run_validate(sources, output, commit=commit)

            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(completed.stdout, "validation passed\n")

    def test_validation_rejects_mutation_without_requiring_an_ownership_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            output = root / "artifact"
            self.assertEqual(run_build(sources, output, commit=commit).returncode, 0)
            (output / "form" / "index.html").write_text("tampered\n", encoding="utf-8")

            completed = run_validate(sources, output, commit=commit)

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("differs from committed source", completed.stdout)

    def test_validation_rejects_an_arbitrary_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            output = root / "arbitrary"
            output.mkdir()
            (output / "keep.txt").write_text("keep\n", encoding="utf-8")

            completed = run_validate(sources, output, commit=commit)

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("unexpected output", completed.stdout)
            self.assertEqual((output / "keep.txt").read_text(encoding="utf-8"), "keep\n")


if __name__ == "__main__":
    unittest.main()
