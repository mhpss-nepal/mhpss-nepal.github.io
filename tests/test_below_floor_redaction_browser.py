#!/usr/bin/env python3
"""Real-browser check of what the public page SHOWS for a below-floor document.

A passing source/Node suite is not evidence that the page works. This drives
the real public page (apps/public/flood-response.html) in headless Chromium,
with its real CSS and its real i18n, and asks the real renderer
(`window.PUBLIC_STATS.preview`) to draw the audit's minimal leaking document.
Then it asserts what a reader can actually SEE and READ.

Synthetic figures only; no network, nothing written anywhere.

Skips when Playwright or its browsers are unavailable.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hub_publish_ui_browser import _serve  # noqa: E402

# The audit's own minimal case: total 100, one visible complement 94, the
# complementary cell 6 hidden. The basis is deliberately digit-free so that a
# figure counted below is a figure of the data, never of the prose.
LEAK = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture: one visible complement, one hidden cell",
    "reports": 100,
    "contacts": 100,
    "organisations": 20,
    "palikas": 8,
    "districts": [
        {"code": "A", "name": "Alpha", "reports": 1, "contacts": 6, "organisations": 1},
        {"code": "B", "name": "Bravo", "reports": 99, "contacts": 94, "organisations": 20},
    ],
    "families": [
        {"family": "small", "contacts": 6},
        {"family": "large", "contacts": 94},
    ],
}

# Identical VISIBLE figures, a different withheld total: the page must not
# change, or it is drawing from a value it is hiding.
LEAK_VARIANT = dict(LEAK)
LEAK_VARIANT["contacts"] = 137
LEAK_VARIANT["reports"] = 137

CLEAN = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture, every count at or above the floor",
    "reports": 200,
    "contacts": 2000,
    "organisations": 20,
    "palikas": 14,
    "districts": [
        {"code": "A", "name": "Alpha", "reports": 100, "contacts": 1000, "organisations": 12},
        {"code": "B", "name": "Bravo", "reports": 100, "contacts": 1000, "organisations": 14},
    ],
    "families": [
        {"family": "one", "contacts": 1000},
        {"family": "two", "contacts": 1000},
    ],
}


def _readable(html: str) -> list[int]:
    text = re.sub(r"<[^>]*>", " ", html)
    return [int(tok.replace(",", "")) for tok in re.findall(r"\d[\d,]*", text)]


@unittest.skipIf(
    importlib.util.find_spec("playwright") is None,
    "Playwright is unavailable to the current interpreter",
)
class BelowFloorRenderBrowserTests(unittest.TestCase):
    def _draw(self, page, doc) -> dict:
        return page.evaluate(
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
                const body = host.querySelector('[data-b]');
                return {
                    html: body.innerHTML,
                    text: body.innerText,
                    zeroWidthBars: body.innerHTML.split('width:0%').length - 1
                };
            }""",
            doc,
        )

    def test_the_real_page_hides_a_below_floor_value(self) -> None:
        from playwright.sync_api import sync_playwright

        server, origin = _serve()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                errors: list[str] = []
                page = browser.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(f"{origin}/flood-response.html", wait_until="load")
                page.wait_for_timeout(800)
                leak = self._draw(page, LEAK)
                clean = self._draw(page, CLEAN)
                variant = self._draw(page, LEAK_VARIANT)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

        self.assertEqual(errors, [], "the real public page raised a script error")

        # the suppressed row and its category are gone, not merely relabelled.
        # (the renderer prints a district by its code and a family by its
        # family key, so those are the categories a reader can see)
        self.assertNotIn("small", leak["text"],
                         "the suppressed family category is still readable")
        self.assertIn("large", leak["text"],
                      "the surviving family row was lost as well")
        self.assertNotIn("fewer than", leak["text"].lower(),
                         "a suppressed row is still drawn as a threshold")

        # the arithmetic channel: a total and its complement must not both be
        # readable while the third cell is hidden
        numbers = _readable(leak["html"])
        self.assertNotIn(6, numbers, "the hidden value is readable on the page")
        self.assertFalse(
            100 in numbers and 94 in numbers,
            "the published total and its complement are both readable, so 100-94=6",
        )

        # geometry: no zero-width bar, which is itself a below-floor tell
        self.assertEqual(leak["zeroWidthBars"], 0, "a zero-width bar was drawn")

        # the page must not depend on anything it has hidden
        self.assertEqual(leak["html"], variant["html"],
                         "the drawn page changes when a withheld value changes")

        # and the redaction must not be a blanket refusal: a clean document
        # still draws its rows and figures
        self.assertIn("one", clean["text"],
                      "a clean document lost its rows: the redaction is too broad")
        self.assertIn("1000", clean["text"].replace(",", ""),
                      "a clean document lost its figures")


if __name__ == "__main__":
    unittest.main()
