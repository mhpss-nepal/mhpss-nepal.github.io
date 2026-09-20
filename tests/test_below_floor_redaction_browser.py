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

# The reviewer's second reproduction: a district row carries its own total AND a
# nested breakdown, one member of which is below the floor. Dropping the nested
# member must withhold the enclosing row total, or 100 - 94 = 6 on the page.
NESTED = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture, nested complementary cell",
    "contacts": 100,
    "districts": [
        {
            "code": "A",
            "name": "Alpha",
            "contacts": 100,
            "breakdown": [
                {"family": "small", "contacts": 6},
                {"family": "large", "contacts": 94},
            ],
        },
    ],
}

MIXED_ROW_FAMILIES = [
    (
        "leading null",
        [None, {"family": "small", "contacts": 6}, {"family": "large", "contacts": 94}],
    ),
    (
        "leading primitive",
        ["unexpected", {"family": "small", "contacts": 6}, {"family": "large", "contacts": 94}],
    ),
]


def mixed_row_document(families):
    return {
        "schema": 1,
        "mode": "production",
        "suppressed_below": 10,
        "basis": "synthetic fixture, malformed mixed row family",
        "contacts": 100,
        "families": families,
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
                const body = host.querySelector('[data-b]');
                try {
                    window.PUBLIC_STATS.preview({
                        state: host.querySelector('[data-s]'),
                        body: body,
                        panel: host,
                        kind: 'flood'
                    }, doc);
                    return {
                        html: body.innerHTML,
                        text: body.innerText,
                        zeroWidthBars: body.innerHTML.split('width:0%').length - 1,
                        error: ''
                    };
                } catch (e) {
                    return {
                        html: body.innerHTML,
                        text: body.innerText,
                        zeroWidthBars: 0,
                        error: String((e && e.message) || e)
                    };
                }
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

    def _redact_on_page(self, page, doc) -> dict:
        return page.evaluate(
            """(doc) => {
                try {
                    return { ok: true, out: window.PUBLIC_STATS.redact(doc), error: '' };
                } catch (e) {
                    return { ok: false, out: null, error: String((e && e.message) || e) };
                }
            }""",
            doc,
        )

    def test_the_real_page_does_not_reconstruct_a_nested_dropped_cell(self) -> None:
        """The reviewer's reproduction at the page's own redaction layer: a
        nested below-floor member must withhold the enclosing row total, so the
        document the page would render from cannot yield 100-94=6."""
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
                redacted = self._redact_on_page(page, NESTED)
                leak = self._draw(page, NESTED)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

        self.assertEqual(errors, [], "the real public page raised a script error")
        self.assertTrue(redacted["ok"], redacted["error"] or "the page could not redact the document")
        body = redacted["out"]
        district = body["districts"][0]
        self.assertIsNone(
            district.get("contacts"),
            "the page kept an enclosing total whose nested component it dropped: 100-94=6",
        )
        # and nothing the page DRAWS carries the surviving nested complement
        numbers = _readable(leak["html"])
        self.assertFalse(
            100 in numbers and 94 in numbers,
            "the enclosing total and the surviving nested complement are both "
            "readable on the page, so 100-94=6",
        )

    def test_the_real_page_refuses_a_value_below_its_effective_floor(self) -> None:
        """A document declaring floor 20 makes 15 below-floor even though it
        clears the default 10. The real page's redaction layer must refuse it
        and draw none of it, rather than show the 15."""
        from playwright.sync_api import sync_playwright

        doc = {
            "schema": 1,
            "mode": "production",
            "suppressed_below": 20,
            "basis": "synthetic fixture, declared floor above default",
            "matrix": [["Org", "RAS", "Palika", "P0001", "A1", "Activity", 15, 15]],
        }
        server, origin = _serve()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                errors: list[str] = []
                page = browser.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(f"{origin}/flood-response.html", wait_until="load")
                page.wait_for_timeout(800)
                redacted = self._redact_on_page(page, doc)
                drawn = self._draw(page, doc)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

        self.assertEqual(errors, [], "the real public page raised a script error")
        self.assertFalse(
            redacted["ok"],
            "the page accepted a value below its effective floor",
        )
        self.assertIn("below-floor", redacted["error"])
        self.assertNotIn("15", drawn["text"],
                         "the page drew a value below its effective floor")

    def test_the_real_page_refuses_mixed_row_families_without_throwing(self) -> None:
        """Leading null/primitive members must not make later aggregate rows
        bypass classification, and the real page must fail closed rather than
        throw while rendering the malformed list."""
        from playwright.sync_api import sync_playwright

        server, origin = _serve()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page()
                page.goto(f"{origin}/flood-response.html", wait_until="load")
                page.wait_for_timeout(800)
                for label, families in MIXED_ROW_FAMILIES:
                    with self.subTest(shape=label):
                        doc = mixed_row_document(families)
                        redacted = self._redact_on_page(page, doc)
                        drawn = self._draw(page, doc)
                        self.assertFalse(redacted["ok"],
                                         f"{label}: page accepted a mixed row family")
                        self.assertIn("mixed row family", redacted["error"].lower())
                        self.assertEqual(drawn["html"], "",
                                         f"{label}: malformed document rendered content")
                        self.assertEqual(drawn["error"], "",
                                         f"{label}: renderer threw instead of failing closed")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()


@unittest.skipIf(
    importlib.util.find_spec("playwright") is None,
    "Playwright is unavailable to the current interpreter",
)
class HubPreviewShowsRedactedTests(unittest.TestCase):
    """The Hub preview must show what would actually be written, not the raw
    computation. A coordinator who pressed Publish on a document with a
    below-floor cell must not have been shown that cell as 'the document as the
    website will read it'."""

    def test_hub_preview_shows_the_redacted_document(self) -> None:
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
                page.evaluate("() => { document.querySelector('.tab[data-p=\"pub\"]').click(); }")
                page.wait_for_selector("#pubDocs .doc", timeout=15000)
                # what the preview would render for one leaking document
                captured = page.evaluate(
                    """async (doc) => {
                        window.PUBLIC_STATS = window.PUBLIC_STATS || { preview() {} };
                        const shown = window.FB.redactPublicBody
                            ? window.FB.redactPublicBody(doc) : doc;
                        return {
                            hasRedact: typeof window.FB.redactPublicBody === 'function',
                            floor: window.FB.REDACTION_FLOOR,
                            written: shown
                        };
                    }""",
                    LEAK,
                )
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

        self.assertEqual(errors, [], "the real Hub page raised a script error")
        self.assertTrue(captured["hasRedact"],
                        "the Hub cannot compute what would be written")
        self.assertGreaterEqual(captured["floor"], 10)
        written = captured["written"]
        self.assertNotIn("A", [d.get("code") for d in written.get("districts", [])],
                         "the Hub preview built from a document with the leaking row still in it")
        self.assertIsNone(written.get("contacts"),
                          "the Hub preview kept a total a dropped row fed")


if __name__ == "__main__":
    unittest.main()
