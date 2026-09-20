#!/usr/bin/env python3
"""Adversarial regressions for the second independent-review fixes.

Every test in this module was written to FAIL against the review-gate baseline
``b1f32cb2ab3f5341b13f7f93b1bb46decab57b6e`` and to pass only once the
code-level blockers are fixed. No existing invariant is weakened: each case
adds a stricter requirement on top of the preserved behavior.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

from fixture_repo import REPOSITORY_ROOT, create_repository, run_build

sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
import layout  # noqa: E402
from layout import json_manifest, validate_path_component  # noqa: E402


def add_and_commit(repository: Path, relative: str, data: bytes) -> str:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _commit_all(repository, f"add {relative!r}")


def replace_and_commit(repository: Path, relative: str, data: bytes) -> str:
    (repository / relative).write_bytes(data)
    return _commit_all(repository, f"replace {relative}")


def _commit_all(repository: Path, message: str) -> str:
    from fixture_repo import commit_all

    return commit_all(repository, message)


class PathCanonicalizationTests(unittest.TestCase):
    """Fix 1: complete Unicode, reserved-name, and canonical-collision policy."""

    def test_every_control_and_format_character_is_rejected(self) -> None:
        controls = [chr(code) for code in range(0x00, 0x20)]
        controls += [chr(0x7F)]
        controls += [chr(code) for code in range(0x80, 0xA0)]
        controls += [
            "\u00ad",  # soft hyphen (format)
            "\u200b",  # zero width space
            "\u200c",  # zero width non-joiner
            "\u200d",  # zero width joiner
            "\u200e",  # left-to-right mark
            "\u200f",  # right-to-left mark
            "\u202a",  # left-to-right embedding
            "\u202e",  # right-to-left override
            "\u2060",  # word joiner
            "\u2066",  # left-to-right isolate
            "\u2069",  # pop directional isolate
            "\ufeff",  # zero width no-break space / BOM
            "\ue000",  # private use (Co)
            "\uf8ff",  # private use (Co)
        ]
        for character in controls:
            with self.subTest(code=f"U+{ord(character):04X}"):
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    validate_path_component(f"a{character}b.html", label="committed source path")

    def test_all_legacy_windows_reserved_name_variants_are_rejected(self) -> None:
        reserved = (
            "CON",
            "con",
            "Con.txt",
            "PRN",
            "prn.log",
            "AUX",
            "aux",
            "NUL",
            "nul.dat",
            "CLOCK$",
            "clock$",
            "CONIN$",
            "CONOUT$",
            "COM1",
            "com9.txt",
            "COM\u00b9",
            "COM\u00b2",
            "COM\u00b3",
            "LPT1",
            "lpt9.dat",
            "LPT\u00b9",
            "LPT\u00b2",
            "LPT\u00b3",
        )
        for name in reserved:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "reserved"):
                    validate_path_component(name, label="committed source path")

    def test_trailing_dot_and_space_components_are_rejected(self) -> None:
        for name in ("name.", "name ", "name...", "name   ", "dot. "):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "trailing"):
                    validate_path_component(name, label="committed source path")

    def test_combined_key_collision_fixture_is_genuinely_combined_only(self) -> None:
        # "Ä" (U+00C4) versus "a" + combining diaeresis (U+0061 U+0308): they
        # differ under plain case-folding and under plain NFC, so they collide
        # only under the combined NFC(path).casefold() key.
        left = "\u00c4.html"
        right = "a\u0308.html"
        self.assertNotEqual(left.casefold(), right.casefold())
        self.assertNotEqual(unicodedata.normalize("NFC", left), unicodedata.normalize("NFC", right))
        self.assertEqual(
            unicodedata.normalize("NFC", left).casefold(),
            unicodedata.normalize("NFC", right).casefold(),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            add_and_commit(repository, f"apps/public/{left}", b"left\n")
            commit = add_and_commit(repository, f"apps/public/{right}", b"right\n")
            completed = run_build(sources, root / "artifact", commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("collision", completed.stdout)

    def test_casefold_and_nfc_collisions_are_still_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            add_and_commit(repository, "apps/public/Note.html", b"upper\n")
            commit = add_and_commit(repository, "apps/public/note.html", b"lower\n")
            self.assertNotEqual(run_build(sources, root / "out-case", commit=commit).returncode, 0)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            add_and_commit(
                repository, "apps/public/" + unicodedata.normalize("NFC", "caf\u00e9") + ".html", b"nfc\n"
            )
            commit = add_and_commit(
                repository, "apps/public/" + unicodedata.normalize("NFD", "caf\u00e9") + ".html", b"nfd\n"
            )
            self.assertNotEqual(run_build(sources, root / "out-nfc", commit=commit).returncode, 0)


class SecretScanningTests(unittest.TestCase):
    """Fix 2: fail-closed, suffix-independent secret scanning with narrow exceptions."""

    def test_assignment_patterns_are_rejected_in_every_allowlisted_type(self) -> None:
        cases = (
            ("apps/public/index.html", b"<html>\nsecret: hunter2\n</html>\n"),
            ("apps/hub/assets/fb.js", b"var x = 1;\nTOKEN = 'abc';\n"),
            ("apps/hub/assets/app.css", b"body{color:red}\nAPI_KEY = abc\n"),
            ("apps/form/icons/icon-192.png", b"\x89PNG\r\npassword = abc\n"),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for index, (relative, data) in enumerate(cases):
                with self.subTest(path=relative):
                    repository, sources, _ = create_repository(root / str(index))
                    commit = replace_and_commit(repository, relative, data)
                    completed = run_build(sources, root / f"out-{index}", commit=commit)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn("forbidden committed source", completed.stdout)

    def test_private_keys_and_service_accounts_are_rejected_regardless_of_suffix(self) -> None:
        cases = (
            ("apps/hub/assets/fb.js", b"/* x */\n-----BEGIN RSA PRIVATE KEY-----\n"),
            ("apps/hub/assets/app.css", b'{"type":"service_account"}\n'),
            ("apps/form/icons/icon-512.png", b'\x89PNG\x00{"private_key_id":"1","client_email":"a@b"}'),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for index, (relative, data) in enumerate(cases):
                with self.subTest(path=relative):
                    repository, sources, _ = create_repository(root / str(index))
                    commit = replace_and_commit(repository, relative, data)
                    completed = run_build(sources, root / f"out-{index}", commit=commit)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn("forbidden committed source", completed.stdout)

    def test_public_firebase_web_config_exception_is_narrow_and_recorded(self) -> None:
        self.assertTrue(layout._PUBLIC_CONFIG_EXCEPTIONS)
        for key, (allowed, reason) in layout._PUBLIC_CONFIG_EXCEPTIONS.items():
            with self.subTest(path=key):
                self.assertEqual(allowed, frozenset({"apikey"}))
                self.assertIn("public", reason.lower())
                self.assertTrue(reason.strip())
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, commit = create_repository(root)
            self.assertEqual(run_build(sources, root / "ok", commit=commit).returncode, 0)
            self.assertTrue((root / "ok" / "hub" / "assets" / "fb-config.js").is_file())

            # A real secret added beside the public web config must still fail.
            leaked = replace_and_commit(
                repository,
                "apps/hub/assets/fb-config.js",
                b"window.FB_CONFIG = { apiKey: 'public-id' };\nserviceToken = 'leak';\n",
            )
            self.assertNotEqual(run_build(sources, root / "leak", commit=leaked).returncode, 0)

            # The same public-config text in a non-allowlisted path must fail.
            copied = replace_and_commit(
                repository,
                "apps/hub/assets/fb.js",
                b"window.FB_CONFIG = { apiKey: 'public-id' };\n",
            )
            self.assertNotEqual(run_build(sources, root / "copied", commit=copied).returncode, 0)


class StrictStructuredDataTests(unittest.TestCase):
    """Fix 3: strict JSON / web-manifest parsing before any output is written."""

    def test_malformed_json_fails_the_build_and_writes_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            commit = replace_and_commit(repository, "apps/hub/data/demo.json", b'{"records": [}\n')
            output = root / "artifact"
            completed = run_build(sources, output, commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("structured", completed.stdout)
            self.assertFalse(output.exists(), "a rejected source must not create the output")

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            commit = replace_and_commit(repository, "apps/hub/data/demo.json", b'{"a": 1, "a": 2}\n')
            completed = run_build(sources, root / "artifact", commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("duplicate", completed.stdout)

    def test_non_finite_json_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            commit = replace_and_commit(repository, "apps/hub/data/demo.json", b'{"reachedTotal": NaN}\n')
            completed = run_build(sources, root / "artifact", commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("non-finite", completed.stdout)

    def test_webmanifest_is_parsed_strictly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for label, payload, needle in (
                ("malformed", b'{"name": "x",}', "structured"),
                ("duplicate", b'{"name": "x", "name": "y"}', "duplicate"),
            ):
                with self.subTest(case=label):
                    repository, sources, _ = create_repository(root / label)
                    commit = replace_and_commit(repository, "apps/form/manifest.webmanifest", payload)
                    completed = run_build(sources, root / f"out-{label}", commit=commit)
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertIn(needle, completed.stdout)


class ManifestIntegrityTests(unittest.TestCase):
    """Fix 4: the manifest covers directories and enforces the collision key."""

    def test_manifest_lists_directories_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            output = root / "artifact"
            self.assertEqual(run_build(sources, output, commit=commit).returncode, 0)
            shown = subprocess.run(
                [sys.executable, str(REPOSITORY_ROOT / "scripts" / "build.py"), "--manifest", str(output)],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(shown.returncode, 0, shown.stdout + shown.stderr)
            manifest = json.loads(shown.stdout)
            self.assertIsInstance(manifest.get("directories"), list)
            paths = {record["path"] for record in manifest["directories"]}
            for required in (".", "form", "hub", "assets", "assets/vendor", "assets/vendor/leaflet"):
                self.assertIn(required, paths)
            self.assertEqual(manifest["total_directories"], len(manifest["directories"]))

    def test_manifest_refuses_canonical_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            root.mkdir(exist_ok=True)
            (root / "\u00c4.html").write_bytes(b"left\n")
            (root / "a\u0308.html").write_bytes(b"right\n")
            with self.assertRaisesRegex(ValueError, "collision"):
                json_manifest(root)

            nested = Path(temporary_directory) / "nested"
            nested.mkdir()
            (nested / "Sub").mkdir()
            (nested / "sub").mkdir()
            with self.assertRaisesRegex(ValueError, "collision"):
                json_manifest(nested)


class NonDestructiveRegressionTests(unittest.TestCase):
    """Fix 6: the fresh-output-only, no-replace guarantees still hold."""

    def test_rejected_source_never_creates_the_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            repository, sources, _ = create_repository(root)
            commit = replace_and_commit(repository, "apps/public/index.html", b"private_key = leak\n")
            output = root / "artifact"
            completed = run_build(sources, output, commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse(output.exists())

    def test_existing_output_is_refused_without_alteration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _, sources, commit = create_repository(root)
            output = root / "artifact"
            output.mkdir()
            sentinel = output / "keep.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            completed = run_build(sources, output, commit=commit)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    def test_no_recursive_delete_primitive_is_introduced(self) -> None:
        text = "\n".join(
            (REPOSITORY_ROOT / "scripts" / name).read_text(encoding="utf-8").lower()
            for name in ("build.py", "layout.py", "validate.py")
        )
        for rejected in ("rmtree", "renameat2", "rename_exchange", "os.replace", "shutil.move"):
            self.assertNotIn(rejected, text)


class QAIsolationTests(unittest.TestCase):
    """Fix 5: exact origin, dynamic port, nonce server identity, narrow fixture."""

    def test_exact_origin_rejects_lookalike_prefixes(self) -> None:
        from qa_harness import canonical_origin, origin_allows

        allowed = "http://127.0.0.1:8000"
        self.assertEqual(canonical_origin(allowed + "/"), allowed)
        self.assertEqual(canonical_origin("http://127.0.0.1:8000/deep/page.html?x=1"), allowed)
        self.assertEqual(canonical_origin("http://LOCALHOST:8000/"), "http://localhost:8000")
        for lookalike in (
            "http://127.0.0.1:80000/",
            "http://127.0.0.1:8000.evil.example/",
            "http://127.0.0.1:8000@evil.example/",
            "http://127.0.0.1@evil.example:8000/",
            "http://127.0.0.1.evil.example:8000/",
            "https://127.0.0.1:8000/",
            "http://127.0.0.1/",
        ):
            with self.subTest(url=lookalike):
                self.assertFalse(origin_allows(lookalike, allowed))
        self.assertTrue(origin_allows("http://127.0.0.1:8000/page", allowed))

    def test_dynamic_port_nonce_identity_and_cleanup(self) -> None:
        from qa_harness import QAFixtureServer

        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture = Path(temporary_directory) / "narrow-fixture"
            fixture.mkdir()
            (fixture / "index.html").write_text("<html>fixture</html>\n", encoding="utf-8")
            server = QAFixtureServer(fixture)
            with server:
                self.assertGreaterEqual(server.port, 1024)
                self.assertNotEqual(server.port, 8000)
                self.assertEqual(server.origin, f"http://127.0.0.1:{server.port}")
                self.assertTrue(server.verify_identity())
                self.assertFalse(server.verify_identity("0" * 64))
                self.assertTrue(server.allows(server.origin + "/"))
                self.assertFalse(server.allows(f"http://127.0.0.1:{server.port}0/"))
                self.assertFalse(server.allows("http://127.0.0.1:1/"))
                self.assertIn(b"fixture", server.fetch("/"))
            self.assertFalse(fixture.exists(), "the dedicated fixture must be removed on teardown")

    def test_fixture_serves_only_a_narrow_scanned_dedicated_directory(self) -> None:
        import qa_harness

        with tempfile.TemporaryDirectory() as temporary_directory:
            dedicated = Path(temporary_directory) / "dedicated"
            dedicated.mkdir()
            (dedicated / "page.html").write_text("<html>ok</html>\n", encoding="utf-8")
            server = qa_harness.QAFixtureServer(dedicated)
            self.assertEqual(server.fixture, dedicated.resolve())

        with self.assertRaisesRegex(ValueError, "dedicated"):
            qa_harness.QAFixtureServer(tempfile.gettempdir())

        with self.assertRaisesRegex(ValueError, "workspace root"):
            qa_harness.QAFixtureServer(REPOSITORY_ROOT)

        with tempfile.TemporaryDirectory() as temporary_directory:
            poisoned = Path(temporary_directory) / "poisoned"
            poisoned.mkdir()
            (poisoned / "config.js").write_text("apiKey = 'leak'\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "secret"):
                qa_harness.QAFixtureServer(poisoned)


if __name__ == "__main__":
    unittest.main()
