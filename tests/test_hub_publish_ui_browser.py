#!/usr/bin/env python3
"""Real-browser check of the Hub publish panel.

A passing source-text suite is not evidence a page works. This drives the real
Hub page in headless Chromium: it loads the in-page synthetic demonstration
data, opens the Publish tab, and asserts what a coordinator actually SEES and
what the Publish button actually collects.

Synthetic data only; no network, no sign-in, nothing is written anywhere.

Skips when Playwright or its browsers are unavailable.
"""

from __future__ import annotations

import importlib.util
import http.server
import socket
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"

# The same real sink harness the source-level gate test drives.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_publication_privacy_gate import publish as sink_publish  # noqa: E402


def _serve() -> tuple[http.server.ThreadingHTTPServer, str]:
    """Serve the three applications at their real addresses (/, /form/, /hub/)."""
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002 - base signature
            """Keep the test output clean."""

        def translate_path(self, path):
            clean = path.split("?", 1)[0].split("#", 1)[0]
            if clean.startswith("/hub/"):
                base = APPS / "hub"
                clean = clean[len("/hub"):]
            elif clean.startswith("/form/"):
                base = APPS / "form"
                clean = clean[len("/form"):]
            else:
                base = APPS / "public"
            target = self.directory_join(base, clean)
            return target

        @staticmethod
        def directory_join(base: Path, clean: str) -> str:
            parts = [p for p in clean.split("/") if p not in ("", ".")]
            resolved = base.joinpath(*parts)
            if clean.endswith("/") or not resolved.suffix:
                resolved = resolved / "index.html"
            return str(resolved)

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


@unittest.skipIf(
    importlib.util.find_spec("playwright") is None,
    "Playwright is unavailable to the current interpreter",
)
class HubPublishUiBrowserTests(unittest.TestCase):
    def test_what_the_page_would_publish_is_refused_by_the_real_sink(self) -> None:
        """End-to-end: capture the documents the real page builds, then feed
        each to the real fb.js public_stats sink. This is the original
        finding's publish path, and it must now fail closed."""
        from playwright.sync_api import sync_playwright

        server, origin = _serve()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page()
                page.goto(f"{origin}/hub/index.html", wait_until="load")
                page.evaluate("() => { document.getElementById('useDemo').click(); }")
                page.wait_for_selector("#app:not([hidden])", timeout=15000)
                page.evaluate(
                    "() => { document.querySelector('.tab[data-p=\"pub\"]').click(); }"
                )
                page.wait_for_selector("#pubDocs .doc", timeout=15000)
                # Capture what the real Publish button sends, without any write.
                page.evaluate(
                    """() => {
                        window.__captured = [];
                        window.FB = window.FB || {};
                        window.FB.publish = function (id, body) {
                            window.__captured.push({id: id, body: body});
                            return Promise.resolve(id);
                        };
                        document.getElementById('pubGo').disabled = false;
                    }"""
                )
                page.evaluate("() => { document.getElementById('pubGo').click(); }")
                page.wait_for_timeout(1500)
                captured = page.evaluate("() => window.__captured")
                self.assertTrue(captured, "the page sent nothing to publish")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

        for item in captured:
            with self.subTest(doc_id=item["id"]):
                self.assertIn(item["body"].get("mode"), ("demonstration", "staged", None))
                result = sink_publish(item["body"], item["id"])
                self.assertEqual(result["writes"], [])
                self.assertTrue(
                    "non-public mode" in result["error"]
                    or "suppression floor" in result["error"],
                    result["error"],
                )

    def test_publish_panel_offers_only_the_two_public_aggregates(self) -> None:
        from playwright.sync_api import sync_playwright

        server, origin = _serve()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                errors: list[str] = []
                page = browser.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(f"{origin}/hub/index.html", wait_until="load")
                page.evaluate("() => { document.getElementById('useDemo').click(); }")
                page.wait_for_selector("#app:not([hidden])", timeout=15000)
                page.evaluate(
                    "() => { document.querySelector('.tab[data-p=\"pub\"]').click(); }"
                )
                page.wait_for_selector("#pubDocs .doc", timeout=15000)
                page.wait_for_timeout(500)

                self.assertEqual(page.locator("#pubDir").count(), 0)
                doc_ids = page.eval_on_selector_all(
                    "#pubDocs .id", "els => els.map(e => e.textContent)"
                )
                self.assertEqual(
                    sorted(doc_ids),
                    ["public_stats/coordination_full", "public_stats/flood_response"],
                )
                boxes = page.eval_on_selector_all(
                    ".pub .chks input[type=checkbox]",
                    "els => els.map(e => e.id)",
                )
                self.assertEqual(sorted(boxes), ["pubFlood", "pubFull"])

                page.evaluate(
                    "() => { document.getElementById('pubPreview').click(); }"
                )
                page.wait_for_selector("#pubPrev .pubprev", timeout=15000)
                page.wait_for_timeout(500)
                shown = page.inner_text("#pubPrev")
                self.assertIn("Flood response summary", shown)
                self.assertNotIn("Referral directory", shown)
                self.assertNotIn("referral_directory", shown)

                # The panel may explain WHY the referral directory is withheld;
                # what must be absent is any way to publish it.
                panel_text = page.inner_text("#p-pub").lower()
                self.assertIn("not publishable", panel_text)
                self.assertNotIn("public_stats/referral_directory", panel_text)
                self.assertEqual(errors, [])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
