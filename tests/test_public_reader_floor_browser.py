#!/usr/bin/env python3
"""Real-browser check of the public reader's suppression floor.

Defence in depth for the guard: even if a document already sitting in
public_stats declares `suppressed_below: 1`, the live public page must still
refuse to show a below-floor value. Drives the real public page in headless
Chromium and asks the real renderer (`window.PUBLIC_STATS.preview`) to draw a
synthetic document.

Synthetic figures only; no network, nothing written anywhere.

Skips when Playwright or its browsers are unavailable.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hub_publish_ui_browser import _serve  # noqa: E402


@unittest.skipIf(
    importlib.util.find_spec("playwright") is None,
    "Playwright is unavailable to the current interpreter",
)
class PublicReaderFloorBrowserTests(unittest.TestCase):
    DOC = {
        "schema": 1,
        "basis": "synthetic fixture for a browser check",
        "suppressed_below": 1,
        "contacts": 100,
        "reports": 100,
        "organisations": 4,
        "palikas": 3,
        "districts": [
            {"code": "RAS", "name": "Rasuwa", "reports": 94, "contacts": 94, "organisations": 4}
        ],
        "families": [{"family": "PSS", "contacts": 6}],
    }

    def test_declared_floor_of_one_cannot_lower_the_page_floor(self) -> None:
        from playwright.sync_api import sync_playwright

        server, origin = _serve()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                errors: list[str] = []
                page = browser.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(f"{origin}/flood-response.html", wait_until="load")
                page.wait_for_timeout(1000)
                drawn = page.evaluate(
                    """(doc) => {
                        const host = document.createElement('div');
                        host.innerHTML = '<p data-s></p><div data-b></div>';
                        document.body.appendChild(host);
                        window.PUBLIC_STATS.preview({
                            state: host.querySelector('[data-s]'),
                            body: host.querySelector('[data-b]'),
                            panel: host,
                            kind: 'flood'
                        }, doc);
                        return host.innerText;
                    }""",
                    self.DOC,
                )
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

        self.assertEqual(errors, [])
        # The exact below-floor value must never be drawn as itself.
        self.assertNotIn("6", drawn.replace("100", "").replace("94", ""))
        # This ticket supersedes "fewer than N": a below-floor row is DROPPED
        # rather than labelled, and its category does not appear either.
        self.assertNotIn("fewer than", drawn.lower())
        self.assertNotIn("PSS", drawn, "the below-floor category is still drawn")
        # The page says the floor it actually used, not the document's claim.
        self.assertIn("10", drawn)


if __name__ == "__main__":
    unittest.main()
