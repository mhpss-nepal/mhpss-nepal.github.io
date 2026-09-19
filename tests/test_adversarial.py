#!/usr/bin/env python3
"""Adversarial regressions for the fail-closed artifact generator."""

from __future__ import annotations

import gc
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import unicodedata
import warnings
from pathlib import Path
from unittest.mock import patch

from fixture_repo import (
    BUILD_SCRIPT,
    REPOSITORY_ROOT,
    TRACKED_APPLICATION_PATHS,
    clean_environment,
    commit_all,
    create_repository,
    run_build,
)

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
from build import build  # noqa: E402
from layout import validate_path_component  # noqa: E402


FAKE_GIT = r'''#!/usr/bin/env python3
import os
import subprocess
import sys

args = sys.argv[1:]
is_batch = "cat-file" in args and "--batch" in args
request = sys.stdin.buffer.read() if is_batch else None
completed = subprocess.run(["/usr/bin/git", *args], input=request, capture_output=True)
out = completed.stdout
target = os.environ.get("FAKE_MUTATE_OID", "")
if completed.returncode == 0 and is_batch and target:
    offset = 0
    changed = bytearray()
    while offset < len(out):
        end = out.find(b"\n", offset)
        if end < 0:
            break
        header = out[offset:end]
        fields = header.split()
        if len(fields) != 3 or not fields[2].isdigit():
            break
        size = int(fields[2])
        start = end + 1
        finish = start + size
        body = bytearray(out[start:finish])
        if fields[0].decode("ascii") == target and body:
            body[0] ^= 1
        changed.extend(header + b"\n" + body + b"\n")
        offset = finish + 1
    if offset == len(out):
        out = bytes(changed)
sys.stdout.buffer.write(out)
sys.stderr.buffer.write(completed.stderr)
raise SystemExit(completed.returncode)
'''


def add_and_commit(repository: Path, relative: str, data: bytes) -> str:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return commit_all(repository, f"add {relative!r}")


def replace_and_commit(repository: Path, relative: str, data: bytes) -> str:
    path = repository / relative
    path.write_bytes(data)
    return commit_all(repository, f"replace {relative}")


class NonDestructiveOutputTests(unittest.TestCase):
    def test_arbitrary_existing_file_or_directory_is_refused_and_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            for kind in ("file", "directory"):
                output = root / kind
                if kind == "file":
                    output.write_text("keep\n", encoding="utf-8")
                    sentinel = output
                else:
                    output.mkdir()
                    sentinel = output / "keep.txt"
                    sentinel.write_text("keep\n", encoding="utf-8")

                completed = run_build(sources, output, commit=commit)

                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("output path already exists", completed.stdout)
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    def test_parent_symlink_substitution_is_refused_without_touching_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            victim = root / "victim"
            victim.mkdir()
            sentinel = victim / "keep.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            parent = root / "substituted-parent"
            parent.symlink_to(victim, target_is_directory=True)

            completed = run_build(sources, parent / "artifact", commit=commit)

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
            self.assertFalse((victim / "artifact").exists())

    def test_parent_substitution_after_descriptor_acquisition_cannot_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            parent = root / "parent"
            parent.mkdir()
            victim = root / "victim"
            victim.mkdir()
            sentinel = victim / "keep.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            moved = root / "moved-parent"

            original = os.mkdir
            swapped = False

            def substitute(path: str, mode: int = 0o777, *, dir_fd: int | None = None) -> None:
                nonlocal swapped
                if path == "artifact" and dir_fd is not None and not swapped:
                    parent.rename(moved)
                    parent.symlink_to(victim, target_is_directory=True)
                    swapped = True
                original(path, mode=mode, dir_fd=dir_fd)

            with patch("build.os.mkdir", side_effect=substitute):
                build(sources, parent / "artifact", commit)

            self.assertTrue((moved / "artifact" / "index.html").is_file())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
            self.assertFalse((victim / "artifact").exists())

    def test_fresh_output_entry_substitution_is_detected_without_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            output = root / "artifact"
            victim = root / "victim"
            victim.mkdir()
            sentinel = victim / "keep.txt"
            sentinel.write_text("keep\n", encoding="utf-8")

            original = os.open
            swapped = False

            def substitute(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
                nonlocal swapped
                if path == "artifact" and dir_fd is not None and flags & os.O_DIRECTORY and not swapped:
                    output.rename(root / "fresh-created")
                    output.symlink_to(victim, target_is_directory=True)
                    swapped = True
                return original(path, flags, mode, dir_fd=dir_fd)

            with patch("build.os.open", side_effect=substitute):
                with self.assertRaises((OSError, ValueError)):
                    build(sources, output, commit)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
            self.assertTrue((root / "fresh-created").is_dir())

    def test_rejected_replacement_mechanisms_are_absent(self) -> None:
        scripts = "\n".join(
            (REPOSITORY_ROOT / "scripts" / name).read_text(encoding="utf-8")
            for name in ("build.py", "layout.py", "validate.py")
        ).lower()
        for rejected in (
            "rmtree",
            "renameat2",
            "rename_exchange",
            "setxattr",
            "getxattr",
            "ownership_xattr",
            "ownership marker",
            "staging",
        ):
            self.assertNotIn(rejected, scripts)


class GitObjectTrustTests(unittest.TestCase):
    def test_bounded_git_process_closes_all_pipe_resources(self) -> None:
        from layout import _bounded_process

        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always", ResourceWarning)
            return_code, stdout, stderr = _bounded_process(
                ["/usr/bin/git", "--version"],
                stdout_limit=1024,
            )
            gc.collect()

        self.assertEqual(return_code, 0)
        self.assertTrue(stdout.startswith(b"git version "))
        self.assertEqual(stderr, b"")
        resource_warnings = [warning for warning in seen if issubclass(warning.category, ResourceWarning)]
        self.assertEqual(resource_warnings, [])

    def test_git_environment_disables_lazy_fetch_and_drops_inherited_git_variables(self) -> None:
        from layout import _git_environment

        with patch.dict(
            os.environ,
            {
                "GIT_DIR": "/attacker",
                "git_work_tree": "/attacker-worktree",
                "UNCHANGED": "kept",
            },
            clear=True,
        ):
            environment = _git_environment()

        self.assertEqual(environment["UNCHANGED"], "kept")
        self.assertNotIn("GIT_DIR", environment)
        self.assertNotIn("git_work_tree", environment)
        self.assertEqual(environment["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")

    def test_all_inherited_git_environment_variables_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root / "wanted", "wanted")
            attacker, _, _ = create_repository(root / "attacker", "attacker")
            output = root / "artifact"
            environment = clean_environment(
                GIT_DIR=str(attacker / ".git"),
                GIT_WORK_TREE=str(attacker),
                GIT_OBJECT_DIRECTORY=str(attacker / ".git" / "objects"),
                GIT_ALTERNATE_OBJECT_DIRECTORIES=str(attacker / ".git" / "objects"),
                GIT_INDEX_FILE=str(attacker / ".git" / "index"),
            )

            completed = run_build(sources, output, commit=commit, environment=environment)

            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(
                (output / "index.html").read_text(encoding="utf-8"),
                "wanted: apps/public/index.html\n",
            )

    def test_replaced_commit_and_tree_object_bytes_fail_hash_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, commit = create_repository(root)
            tree = subprocess.run(
                ["/usr/bin/git", "-C", str(repository), "show", "-s", "--format=%T", commit],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            bin_dir = root / "bin"
            bin_dir.mkdir()
            wrapper = bin_dir / "git"
            wrapper.write_text(FAKE_GIT, encoding="utf-8")
            wrapper.chmod(0o755)

            for label, oid in (("commit", commit), ("tree", tree)):
                with self.subTest(object_type=label):
                    output = root / f"artifact-{label}"
                    environment = clean_environment(
                        PATH=str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
                        FAKE_MUTATE_OID=oid,
                    )
                    completed = run_build(sources, output, commit=commit, environment=environment)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn("object-id verification", completed.stdout)


class FilenameSafetyTests(unittest.TestCase):
    def test_unsafe_and_ambiguous_committed_names_are_rejected(self) -> None:
        cases = (
            ("control", "apps/public/bad\nname.html", b"x\n"),
            ("windows", "apps/public/CON.txt", b"x\n"),
            ("trailing", "apps/public/trailing. ", b"x\n"),
            ("casefold", "apps/public/readme.md", b"x\n"),
            ("unicode", "apps/public/" + unicodedata.normalize("NFD", "café") + ".html", b"x\n"),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for label, relative, data in cases:
                with self.subTest(case=label):
                    repository, sources, _ = create_repository(root / label)
                    if label == "unicode":
                        other = repository / ("apps/public/" + unicodedata.normalize("NFC", "café") + ".html")
                        other.write_bytes(b"other\n")
                    commit = add_and_commit(repository, relative, data)
                    completed = run_build(sources, root / f"out-{label}", commit=commit)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertRegex(completed.stdout, "unsafe|ambiguous|collision|unclassified|\\.git")

        for spelling in (".git", ".GIT", ".GiT", ".gIt"):
            with self.subTest(case=spelling):
                with self.assertRaisesRegex(ValueError, "\\.git"):
                    validate_path_component(spelling, label="committed source path")

    def test_unclassified_extra_application_blob_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            commit = add_and_commit(repository, "apps/public/extra.html", b"extra\n")

            completed = run_build(sources, root / "artifact", commit=commit)

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("unclassified application path", completed.stdout)


class ResourceLimitTests(unittest.TestCase):
    def test_per_file_total_path_depth_path_length_and_traversal_limits(self) -> None:
        cases = {
            "per-file": ("apps/public/index.html", b"x" * (1024 * 1024 + 1), False),
            "depth": ("apps/public/" + "/".join(["d"] * 13) + "/x", b"x", True),
            "length": ("apps/public/" + "x" * 241, b"x", True),
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for label, (relative, data, add) in cases.items():
                with self.subTest(limit=label):
                    repository, sources, _ = create_repository(root / label)
                    commit = (
                        add_and_commit(repository, relative, data)
                        if add
                        else replace_and_commit(repository, relative, data)
                    )
                    completed = run_build(sources, root / f"out-{label}", commit=commit)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn("limit", completed.stdout)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            for index in range(2):
                path = repository / "apps" / "public" / f"extra-{index}.html"
                path.write_text("x", encoding="utf-8")
            commit = commit_all(repository, "exceed total files")
            completed = run_build(sources, root / "out-files", commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("total file limit", completed.stdout)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            for relative in TRACKED_APPLICATION_PATHS:
                (repository / relative).write_bytes(b"x" * 70000)
            commit = commit_all(repository, "exceed total bytes")
            completed = run_build(sources, root / "out-total", commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("total byte limit", completed.stdout)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            for index in range(400):
                path = repository / "apps" / "public" / "work" / f"d{index}" / "x"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            commit = commit_all(repository, "exceed application traversal work")
            completed = run_build(sources, root / "out-work", commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("traversal work limit", completed.stdout)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            for index in range(300):
                path = repository / f"root-entry-{index:03d}"
                path.write_text("x", encoding="utf-8")
            commit = commit_all(repository, "exceed root traversal work")
            completed = run_build(sources, root / "out-root-work", commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("traversal work limit", completed.stdout)


class ForbiddenArtifactTests(unittest.TestCase):
    def test_delayed_private_key_marker_is_scanned_across_the_entire_bounded_blob(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            content = b"A" * 20000 + b"-----BEGIN PRIVATE KEY-----\n"
            commit = replace_and_commit(repository, "apps/public/index.html", content)

            completed = run_build(sources, root / "artifact", commit=commit)

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("private-key material", completed.stdout)

    def test_envrc_token_snapshot_spreadsheet_delimited_and_dump_artifacts_are_rejected(self) -> None:
        forbidden = (
            ("apps/public/.envrc", b"TOKEN=secret\n"),
            ("apps/public/token", b"token=secret\n"),
            ("apps/public/config.txt", b"password = secret\n"),
            ("apps/form/snapshot.json", b"{}\n"),
            ("apps/form/exports/current.json", b"{}\n"),
            ("apps/hub/backup/data.json", b"{}\n"),
            ("apps/hub/report.ods", b"sheet\n"),
            ("apps/hub/report.psv", b"a|b\n"),
            ("apps/hub/database.sql", b"CREATE TABLE x;\n"),
            ("apps/hub/key.json", b'{"type":"service_account"}\n'),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for index, (relative, data) in enumerate(forbidden):
                with self.subTest(path=relative):
                    repository, sources, _ = create_repository(root / str(index))
                    commit = add_and_commit(repository, relative, data)
                    completed = run_build(sources, root / f"out-{index}", commit=commit)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn("forbidden committed source", completed.stdout)

    def test_repository_ignore_backstop_covers_forbidden_artifact_classes(self) -> None:
        candidates = (
            "apps/public/.envrc",
            "apps/public/token",
            "apps/public/secrets/config.txt",
            "apps/form/snapshot.json",
            "apps/form/exports/current.js",
            "apps/hub/backups/current.js",
            "apps/hub/report.ods",
            "apps/hub/report.psv",
            "apps/hub/database.sql",
            "apps/hub/service-account.json",
        )
        completed = subprocess.run(
            ["git", "check-ignore", "--no-index", *candidates],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(set(completed.stdout.splitlines()), set(candidates))

    def test_only_documented_synthetic_demo_json_and_js_are_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, commit = create_repository(root)
            output = root / "artifact"
            completed = run_build(sources, output, commit=commit)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue((output / "hub" / "data" / "demo.json").is_file())
            self.assertTrue((output / "hub" / "data" / "demo.js").is_file())

            replace_and_commit(
                repository,
                "apps/hub/data/README.md",
                b"# Data\n\nExamples.\n",
            )
            changed_commit = subprocess.run(
                ["/usr/bin/git", "-C", str(repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            rejected = run_build(sources, root / "artifact-undocumented", commit=changed_commit)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("synthetic demo allowlist", rejected.stdout)


if __name__ == "__main__":
    unittest.main()
