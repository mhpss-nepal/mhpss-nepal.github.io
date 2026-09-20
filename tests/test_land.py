#!/usr/bin/env python3
"""Fail-closed tests for the verified frontend landing procedure."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fixture_repo import REPOSITORY_ROOT, TRACKED_APPLICATION_PATHS, create_repository, run_build

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import land  # noqa: E402

LAND_SCRIPT = REPOSITORY_ROOT / "scripts" / "land.py"

EXPECTED_ORIGINS = {
    "public": "git@github.com:mhpss-nepal/mhpss-nepal.github.io.git",
    "form": "git@github.com:mhpss-nepal/form.git",
    "hub": "git@github.com:mhpss-nepal/hub.git",
}

# A small classified set the fixture monorepo can build and land against.
EXPECTED_APP_PATHS = (
    "apps/form/index.html",
    "apps/hub/index.html",
    "apps/public/index.html",
)


def git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=check,
        capture_output=True,
        text=True,
    )


def write_raw_object(repository: Path, object_type: str, data: bytes) -> str:
    """Write one Git object directly so malformed trees can be constructed.

    Git's own index-writing commands refuse to create a gitlink or a ``.git``
    tree entry, so the only way to build these adversarial fixtures is to place
    the compressed object and commit into the repository by hand.
    """
    import binascii
    import hashlib
    import zlib

    raw = f"{object_type} {len(data)}".encode("ascii") + b"\0" + data
    oid = hashlib.sha1(raw).hexdigest()
    directory = repository / ".git" / "objects" / oid[:2]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / oid[2:]).write_bytes(zlib.compress(raw))
    return oid


def raw_commit(repository: Path, entries: list[tuple[str, str, bytes | str]]) -> str:
    """Commit a single-level tree of ``(mode, name, blob-bytes-or-sha)`` entries."""
    import binascii

    body = bytearray()
    for mode, name, payload in entries:
        if isinstance(payload, bytes):
            oid = write_raw_object(repository, "blob", payload)
        else:
            oid = payload
        body += mode.encode("ascii") + b" " + name.encode("utf-8") + b"\0" + binascii.unhexlify(oid)
    tree = write_raw_object(repository, "tree", bytes(body))
    commit_body = (
        f"tree {tree}\nauthor Fixture <fixture@example.invalid> 0 +0000\n"
        f"committer Fixture <fixture@example.invalid> 0 +0000\n\nmalformed tree\n"
    ).encode("utf-8")
    return write_raw_object(repository, "commit", commit_body)


def commit(repository: Path, message: str) -> str:
    git(repository, "add", "-A", "-f")
    git(
        repository,
        "-c",
        "user.name=Fixture Author",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )
    return git(repository, "rev-parse", "HEAD").stdout.strip()


def make_source(root: Path, target: str, files: dict[str, bytes] | None = None) -> tuple[Path, str]:
    repository = root / f"{target}-source"
    repository.mkdir(parents=True)
    git(repository, "init", "-q")
    git(repository, "remote", "add", "origin", EXPECTED_ORIGINS[target])
    for relative, data in (files or {"index.html": b"<html>new</html>\n"}).items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return repository, commit(repository, "source candidate")


def write_path_manifest(repository: Path, paths: tuple[str, ...] | None = None) -> tuple[str, ...]:
    if paths is None:
        paths = tuple(
            sorted(
                path.relative_to(repository).as_posix()
                for app in (repository / "apps").iterdir()
                for path in app.rglob("*")
                if path.is_file()
            )
        )
    manifest = repository / "config" / "application-paths.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps({"paths": sorted(paths), "schema": 1}, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return tuple(paths)


def make_monorepo(root: Path) -> tuple[Path, str]:
    repository = root / "monorepo"
    for app in ("public", "form", "hub"):
        path = repository / "apps" / app / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"<html>{app}-old</html>\n", encoding="utf-8")
    (repository / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
    write_path_manifest(repository, EXPECTED_APP_PATHS)
    (repository / "provenance").mkdir()
    (repository / "provenance" / "frontend-sources.json").write_text(
        json.dumps({"applications": {}, "schema": 1}, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    git(repository, "init", "-q")
    baseline = commit(repository, "monorepo baseline")
    return repository, baseline


def run_land(
    monorepo: Path,
    source: Path,
    sha: str,
    target: str,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(LAND_SCRIPT),
            "--monorepo",
            str(monorepo),
            "--source-repo",
            str(source),
            "--commit",
            sha,
            "--target-app",
            target,
            *extra,
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )


class InputValidationTests(unittest.TestCase):
    def test_rejects_branch_short_sha_and_missing_full_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, sha = make_source(root, "public")
            monorepo, _ = make_monorepo(root)
            for revision in ("HEAD", sha[:12], "0" * 40):
                with self.subTest(revision=revision):
                    completed = run_land(monorepo, source, revision, "public")
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertRegex(completed.stderr, "full commit|does not exist")

    def test_rejects_wrong_repository_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, sha = make_source(root, "public")
            git(source, "remote", "set-url", "origin", "git@github.com:someone/wrong.git")
            monorepo, _ = make_monorepo(root)
            completed = run_land(monorepo, source, sha, "public")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("repository identity", completed.stderr)

    def test_rejects_dirty_source_and_dirty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, sha = make_source(root, "public")
            monorepo, _ = make_monorepo(root)
            (source / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            completed = run_land(monorepo, source, sha, "public")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("source worktree is dirty", completed.stderr)

            (source / "untracked.txt").unlink()
            (monorepo / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            completed = run_land(monorepo, source, sha, "public")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("monorepo worktree is dirty", completed.stderr)


class AdversarialSourceTests(unittest.TestCase):
    def test_no_remote_or_rewriting_git_subcommand_is_used(self) -> None:
        import ast

        banned = {
            "push", "fetch", "pull", "clone", "merge", "rebase", "reset",
            "gc", "repack", "prune", "filter-branch", "filter-repo",
            "clean", "checkout", "switch", "restore", "branch", "tag", "update-ref",
            "replace", "commit", "commit-tree", "reflog", "worktree", "submodule",
        }
        # ``remote get-url`` only reads the configured origin for the identity
        # check; every other ``remote`` action mutates configuration and is banned.
        allowed = {("remote", "get-url")}
        commands: list[tuple[str, ...]] = []
        for name in ("land.py", "layout.py", "build.py", "validate.py"):
            tree = ast.parse((REPOSITORY_ROOT / "scripts" / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_git":
                    constants = [
                        argument.value
                        for argument in node.args[2:]
                        if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
                    ]
                    if constants:
                        commands.append(tuple(constants))
        self.assertTrue(commands)
        for command in commands:
            self.assertNotIn(command[0], banned, command)
            if command[0] == "remote":
                self.assertIn(command[:2], allowed, command)

    def assert_rejected(self, files: dict[str, bytes], needle: str) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, sha = make_source(root, "public", files)
            monorepo, _ = make_monorepo(root)
            completed = run_land(monorepo, source, sha, "public")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(needle, completed.stderr)
            self.assertEqual(git(monorepo, "status", "--porcelain").stdout, "")

    def test_unclassified_file_fails_closed(self) -> None:
        self.assert_rejected({"index.html": b"ok\n", "payload.exe": b"binary\n"}, "unclassified")

    def test_path_collision_fails_closed(self) -> None:
        self.assert_rejected(
            {"index.html": b"ok\n", "Note.html": b"one\n", "note.html": b"two\n"},
            "collision",
        )

    def test_secret_shaped_blob_fails_closed(self) -> None:
        self.assert_rejected(
            {"index.html": b"<html>ok</html>\n", "assets/app.js": b"serviceToken = 'not-public'\n"},
            "secret/token/password",
        )

    def test_gitlink_submodule_entry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, _ = make_source(root, "public", {"index.html": b"ok\n"})
            sha = raw_commit(source, [("160000", "vendored", "0" * 40)])
            monorepo, _ = make_monorepo(root)
            completed = run_land(monorepo, source, sha, "public")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("gitlink or special mode", completed.stderr)

    def test_repository_metadata_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, _ = make_source(root, "public", {"index.html": b"ok\n"})
            sha = raw_commit(source, [("100644", ".git", b"metadata\n")])
            monorepo, _ = make_monorepo(root)
            completed = run_land(monorepo, source, sha, "public")
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("repository metadata", completed.stderr)

    def test_parity_check_rejects_a_dropped_file(self) -> None:
        expected = (
            land.LandingFile("a.html", b"a\n"),
            land.LandingFile("b.css", b"b\n"),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            candidate = Path(temporary_directory)
            (candidate / "a.html").write_bytes(b"a\n")
            with self.assertRaisesRegex(ValueError, "missing imported file: b.css"):
                land.verify_tree_parity(expected, candidate)


class CrossApplicationContractTests(unittest.TestCase):
    def test_new_form_hub_asset_dependency_requires_recorded_override(self) -> None:
        files = {
            "index.html": b'<link rel="stylesheet" href="../hub/assets/app.css">\n',
            "new.html": b'<script src="../hub/assets/new-runtime.js"></script>\n',
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, sha = make_source(root, "form", files)
            monorepo, _ = make_monorepo(root)
            (monorepo / "apps" / "form" / "index.html").write_bytes(files["index.html"])
            write_path_manifest(monorepo)
            commit(monorepo, "record existing form dependency")

            blocked = run_land(monorepo, source, sha, "form")
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("cross-application runtime dependency", blocked.stderr)

            allowed = run_land(
                monorepo,
                source,
                sha,
                "form",
                "--acknowledge-cross-app-dependency",
                "Coordinated Hub asset addition will be reviewed as one release pair.",
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            report = json.loads(allowed.stdout)
            self.assertTrue(report["cross_application_dependency"]["acknowledged"])
            self.assertIn("new-runtime.js", json.dumps(report["cross_application_dependency"]))


class LandingBehaviorTests(unittest.TestCase):
    def test_dry_run_reports_provenance_changes_and_per_file_parity_without_mutation(self) -> None:
        files = {
            "index.html": b"<html>new</html>\n",
            "assets/site.css": b"body { color: navy; }\n",
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, sha = make_source(root, "public", files)
            monorepo, baseline = make_monorepo(root)
            completed = run_land(monorepo, source, sha, "public")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["mode"], "dry-run")
            self.assertEqual(report["source"]["commit"], sha)
            self.assertEqual(report["source"]["author"], "Fixture Author <fixture@example.invalid>")
            self.assertTrue(report["parity_verified"])
            self.assertEqual(report["previous"]["file_count"], 1)
            self.assertEqual(report["candidate"]["file_count"], 2)
            self.assertEqual(report["changes"]["added"], ["assets/site.css"])
            self.assertEqual(report["changes"]["removed"], [])
            self.assertEqual(report["changes"]["changed"], ["index.html"])
            manifest = {item["path"]: item for item in report["candidate"]["files"]}
            self.assertEqual(manifest["assets/site.css"]["size"], len(files["assets/site.css"]))
            self.assertEqual(manifest["assets/site.css"]["sha256"], hashlib.sha256(files["assets/site.css"]).hexdigest())
            self.assertEqual(git(monorepo, "rev-parse", "HEAD").stdout.strip(), baseline)
            self.assertEqual(git(monorepo, "status", "--porcelain").stdout, "")

    def test_apply_replaces_exact_target_updates_allowlist_and_records_rederivable_provenance(self) -> None:
        files = {
            "index.html": b"<html>landed</html>\n",
            "assets/site.css": b"body { color: teal; }\n",
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, sha = make_source(root, "public", files)
            monorepo, baseline = make_monorepo(root)
            completed = run_land(monorepo, source, sha, "public", "--apply")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["mode"], "apply")
            self.assertTrue(report["parity_verified"])
            actual = {
                path.relative_to(monorepo / "apps" / "public").as_posix(): path.read_bytes()
                for path in (monorepo / "apps" / "public").rglob("*")
                if path.is_file()
            }
            self.assertEqual(actual, files)
            configured = json.loads((monorepo / "config" / "application-paths.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [path for path in configured["paths"] if path.startswith("apps/public/")],
                ["apps/public/assets/site.css", "apps/public/index.html"],
            )
            provenance = json.loads(
                (monorepo / "provenance" / "frontend-sources.json").read_text(encoding="utf-8")
            )
            record = provenance["applications"]["public"]
            self.assertEqual(record["commit"], sha)
            self.assertEqual(record["repository"], EXPECTED_ORIGINS["public"])
            self.assertIn("--commit " + sha, record["rederive_command"])
            self.assertEqual(git(monorepo, "rev-parse", "HEAD").stdout.strip(), baseline)
            self.assertNotEqual(git(monorepo, "status", "--porcelain").stdout, "")

    def test_apply_removes_classified_paths_dropped_by_the_source_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            monorepo, _ = make_monorepo(root)
            (monorepo / "apps" / "public" / "old.html").write_bytes(b"old\n")
            write_path_manifest(monorepo, (*EXPECTED_APP_PATHS, "apps/public/old.html"))
            commit(monorepo, "add a path the source later drops")
            source, sha = make_source(root, "public", {"index.html": b"<html>new</html>\n"})
            completed = run_land(monorepo, source, sha, "public", "--apply")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["changes"]["removed"], ["old.html"])
            self.assertFalse((monorepo / "apps" / "public" / "old.html").exists())
            configured = json.loads((monorepo / "config" / "application-paths.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [path for path in configured["paths"] if path.startswith("apps/public/")],
                ["apps/public/index.html"],
            )

    def test_untracked_ignored_debris_is_not_compared_or_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, sha = make_source(root, "public", {"index.html": b"<html>new</html>\n"})
            monorepo, _ = make_monorepo(root)
            debris = monorepo / "apps" / "public" / "tools" / "__pycache__"
            debris.mkdir(parents=True)
            cache = debris / "helper.cpython-311.pyc"
            cache.write_bytes(b"cache\n")
            completed = run_land(monorepo, source, sha, "public", "--apply")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertIn("tools/__pycache__/helper.cpython-311.pyc", report["unclassified_present_before"])
            self.assertEqual(report["changes"]["removed"], [])
            self.assertTrue(cache.exists())

    def test_builder_accepts_a_new_classified_path_only_after_manifest_is_updated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            added = repository / "apps" / "public" / "new-page.html"
            added.write_text("<html>new page</html>\n", encoding="utf-8")
            rejected_commit = commit(repository, "new page without manifest")
            rejected = run_build(sources, root / "rejected", commit=rejected_commit)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("unclassified application path", rejected.stdout)

            write_path_manifest(repository, (*TRACKED_APPLICATION_PATHS, "apps/public/new-page.html"))
            accepted_commit = commit(repository, "classify new page")
            accepted = run_build(sources, root / "accepted", commit=accepted_commit)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            self.assertTrue((root / "accepted" / "new-page.html").is_file())


if __name__ == "__main__":
    unittest.main()
