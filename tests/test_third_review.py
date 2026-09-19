#!/usr/bin/env python3
"""Deployment-gate, UI-claim, and QA-helper regressions."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fixture_repo import REPOSITORY_ROOT


class DeploymentGateTests(unittest.TestCase):
    def test_infrastructure_docs_keep_the_unverified_rules_deployment_gate(self) -> None:
        text = (REPOSITORY_ROOT / "infra" / "README.md").read_text(encoding="utf-8").lower()
        for required in (
            "authoritative firestore rules are not yet versioned or verified",
            "must not be deployed",
            "exported",
            "reviewed",
            "emulator-tested",
            "coordinated",
        ):
            self.assertIn(required, text)

    def test_client_ui_and_comments_do_not_claim_unverified_rule_behavior_or_role_key(self) -> None:
        paths = (
            REPOSITORY_ROOT / "apps" / "hub" / "assets" / "fb.js",
            REPOSITORY_ROOT / "apps" / "hub" / "access.html",
            REPOSITORY_ROOT / "apps" / "hub" / "forms.html",
            REPOSITORY_ROOT / "apps" / "hub" / "index.html",
            REPOSITORY_ROOT / "apps" / "hub" / "README.md",
            REPOSITORY_ROOT / "README.md",
        )
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        lowered = text.lower()
        self.assertIn("server enforcement is unverified", lowered)
        for unsupported in (
            r"roles/\{uid\}",
            r"roles/\{email\}",
            r"rules v\d",
            r"the rules require",
            r"the rules let",
            r"server-side rules remaining authoritative",
        ):
            self.assertIsNone(re.search(unsupported, lowered), unsupported)

    def test_no_personal_email_or_privileged_owner_client_path(self) -> None:
        bridge = (REPOSITORY_ROOT / "apps" / "hub" / "assets" / "fb.js").read_text(encoding="utf-8")
        index = (REPOSITORY_ROOT / "apps" / "hub" / "index.html").read_text(encoding="utf-8")
        tracked = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in (REPOSITORY_ROOT / "apps").rglob("*")
            if path.is_file()
        ).lower()
        self.assertNotIn("gmail" + ".com", tracked)
        self.assertNotIn("var " + "OWNER", bridge)
        self.assertNotIn("owner: " + "true", bridge)
        self.assertNotIn("r." + "owner", index)
        self.assertNotIn("mine." + "owner", index)


class LocalQAServerSafetyTests(unittest.TestCase):
    HELPERS = (
        "apps/public/tools/justify-sweep.py",
        "apps/public/tools/contrast-sweep.py",
        "apps/hub/tools/justify-sweep.py",
        "apps/hub/tools/contrast-sweep.py",
    )

    def test_browser_helpers_bind_loopback_and_reap_their_server(self) -> None:
        for relative in self.HELPERS:
            with self.subTest(relative=relative):
                text = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
                self.assertIn('"--bind", "127.0.0.1"', text)
                self.assertIn("srv.terminate()", text)
                self.assertIn("srv.wait(", text)
                self.assertIn("srv.kill()", text)
                self.assertIn("urlopen", text)
                self.assertIn('"--directory"', text)
                self.assertIn("Path(__file__).resolve()", text)
                self.assertIn('ctx.route("**/*", local_only)', text)
                self.assertIn('route.request.url.startswith("http://127.0.0.1:")', text)

    def test_hub_active_layer_number_uses_text_safe_blue(self) -> None:
        css = (REPOSITORY_ROOT / "apps" / "hub" / "assets" / "design.css").read_text(encoding="utf-8")
        self.assertIn(".rail .lyr.on b{background:var(--wh-d);color:#fff}", css)

    def test_browser_helpers_serve_the_application_root_from_any_cwd(self) -> None:
        if importlib.util.find_spec("playwright") is None:
            self.skipTest("Playwright is unavailable to the current interpreter")
        for relative in self.HELPERS:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as cwd:
                completed = subprocess.run(
                    [sys.executable, str(REPOSITORY_ROOT / relative)],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertNotIn("Error code explanation: 404", completed.stdout)


if __name__ == "__main__":
    unittest.main()
