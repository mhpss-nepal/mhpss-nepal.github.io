#!/usr/bin/env python3
"""Failing-first runtime tests for the referral safeguarding gate.

The gate is a control only if it also holds when the form's button handler is
skipped. These tests therefore drive the shared write boundary (l1.js) and the
queue/retry boundary (fb.js) directly, in a real JavaScript engine, and check
that an unticked referral cannot be saved, queued or flushed - and that a ticked
one still saves and queues normally.

Synthetic records only. No real safeguarding case is created or transmitted.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
L1_PATH = ROOT / "apps" / "hub" / "assets" / "l1.js"
FB_PATH = ROOT / "apps" / "hub" / "assets" / "fb.js"
REFERRAL_PATH = ROOT / "apps" / "form" / "referral.html"

# Runs l1.js then fb.js in a shared VM context, then performs one action and
# prints a JSON result. Kept in the test file so the runtime behaviour, not a
# copy of the code, is what is asserted.
NODE_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");

function makeStorage() {
  const values = new Map();
  return {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
    removeItem(key) { values.delete(key); }
  };
}

function stubEl() {
  return { className: "", innerHTML: "", textContent: "", style: {},
           appendChild() {}, insertBefore() {}, parentNode: null,
           onclick: null, disabled: false, focus() {}, click() {} };
}

const localStorage = makeStorage();
const document = {
  title: "test",
  readyState: "complete",
  addEventListener() {},
  querySelectorAll() { return []; },
  createElement() { return stubEl(); },
  getElementById() { return null; },
  head: stubEl(),
  body: Object.assign(stubEl(), { firstElementChild: null })
};
const window = {
  FB_CONFIG: {},
  FB_COLLECTION: "submissions",
  addEventListener() {},
  history: { replaceState() {} },
  location: { href: "http://test/referral.html", pathname: "/referral.html", search: "", origin: "http://test" },
  prompt() { return ""; }
};
const context = {
  window, document, localStorage,
  navigator: { onLine: false },
  console,
  Blob: function () {},
  URL: { createObjectURL() { return "blob:test"; }, revokeObjectURL() {} },
  setTimeout, clearTimeout,
  CustomEvent: function (name) { this.type = name; },
  Date, JSON, Math, Promise
};
window.window = window; window.document = document; window.localStorage = localStorage;
vm.createContext(context);
if (process.argv[3] !== "queue-unsafe-no-l1") {
  vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context, { filename: "l1.js" });
}
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context, { filename: "fb.js" });

const UNSAFE = {
  schema: "mhpss-np-referral/0.1.0-draft",
  kind: "referral",
  district: "RAS",
  safeguarding_confirmed: false,
  excludes_gbv_uasc_lifethreat: false
};
const SAFE = {
  schema: "mhpss-np-referral/0.1.0-draft",
  kind: "referral",
  district: "RAS",
  safeguarding_confirmed: true,
  excludes_gbv_uasc_lifethreat: true
};
const QUEUE_KEY = "mhpss-np-queue-v1";
const L1_KEY = "mhpss-np-l1-referral-v1";

function capture(fn) {
  try { return { value: fn(), error: "" }; }
  catch (caught) { return { value: undefined, error: String(caught && caught.message || caught) }; }
}

async function main(action) {
  if (action === "direct-unsafe") {
    const out = capture(() => window.L1.save("referral", UNSAFE));
    return { error: out.error, saved: window.L1.all("referral").length, queued: window.FB.queue().length };
  }
  if (action === "direct-unsafe-untyped") {
    const untyped = {
      district: "RAS",
      safeguarding_confirmed: false,
      excludes_gbv_uasc_lifethreat: false
    };
    const out = capture(() => window.L1.save("referral", untyped));
    return { error: out.error, saved: window.L1.all("referral").length, queued: window.FB.queue().length };
  }
  if (action === "direct-safe") {
    const out = capture(() => window.L1.save("referral", SAFE));
    return { error: out.error, saved: window.L1.all("referral").length, queued: window.FB.queue().length };
  }
  if (action === "direct-safe-untyped") {
    const untyped = {
      district: "RAS",
      safeguarding_confirmed: true,
      excludes_gbv_uasc_lifethreat: true
    };
    const out = capture(() => window.L1.save("referral", untyped));
    return { error: out.error, saved: window.L1.all("referral").length, queued: window.FB.queue().length };
  }
  if (action === "queue-unsafe") {
    const out = await window.FB.submit(UNSAFE).then(
      () => ({ error: "" }), (e) => ({ error: String(e && e.message || e) }));
    return { error: out.error, queued: window.FB.queue().length };
  }
  if (action === "queue-unsafe-no-l1") {
    const out = await window.FB.submit(UNSAFE).then(
      () => ({ error: "" }), (e) => ({ error: String(e && e.message || e) }));
    return { error: out.error, queued: window.FB.queue().length };
  }
  if (action === "queue-unsafe-untyped") {
    const untyped = { district: "RAS", safeguarding_confirmed: false, excludes_gbv_uasc_lifethreat: false };
    const out = await window.FB.submit(untyped).then(
      () => ({ error: "" }), (e) => ({ error: String(e && e.message || e) }));
    return { error: out.error, queued: window.FB.queue().length };
  }
  if (action === "queue-safe") {
    const out = await window.FB.submit(SAFE).then(
      () => ({ error: "" }), (e) => ({ error: String(e && e.message || e) }));
    return { error: out.error, queued: window.FB.queue().length };
  }
  if (action === "retry-unsafe") {
    localStorage.setItem(QUEUE_KEY, JSON.stringify([UNSAFE]));
    await window.FB.flush();
    return { queued: window.FB.queue().length, pending: window.FB.status().pending };
  }
  if (action === "retry-unsafe-untyped") {
    const untyped = { district: "RAS", safeguarding_confirmed: false, excludes_gbv_uasc_lifethreat: false };
    localStorage.setItem(QUEUE_KEY, JSON.stringify([untyped]));
    await window.FB.flush();
    return { queued: window.FB.queue().length, pending: window.FB.status().pending };
  }
  if (action === "reopened-unsafe") {
    localStorage.setItem(L1_KEY, JSON.stringify([UNSAFE]));
    const reopened = window.L1.all("referral")[0];
    const load = capture(() => window.L1.save("referral", reopened));
    return { error: load.error, saved: window.L1.all("referral").length, queued: window.FB.queue().length };
  }
  if (action === "reopened-safe") {
    localStorage.setItem(L1_KEY, JSON.stringify([SAFE]));
    const reopened = window.L1.all("referral")[0];
    const load = capture(() => window.L1.save("referral", reopened));
    return { error: load.error, saved: window.L1.all("referral").length };
  }
  if (action === "non-referral-unaffected") {
    /* the gate must not touch a form that is not the referral */
    const out = capture(() => window.L1.save("contact", { kind: "contact", district: "RAS" }));
    return { error: out.error, saved: window.L1.all("contact").length };
  }
  throw new Error("unknown action: " + action);
}

main(process.argv[3])
  .then((result) => process.stdout.write(JSON.stringify(result)))
  .catch((error) => { console.error(error); process.exit(1); });
"""


class ReferralSafeguardingGateTests(unittest.TestCase):
    def run_node(self, action: str) -> dict[str, object]:
        completed = subprocess.run(
            ["node", "-e", NODE_HARNESS, str(L1_PATH), str(FB_PATH), action],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        return json.loads(completed.stdout)

    def assert_blocked(self, error: str) -> None:
        self.assertIn("STOP", error)
        self.assertIn("Do not record this case here", error)
        self.assertIn("specialised route", error)
        self.assertIn("यहाँ अभिलेख नगर्नुहोस्", error)
        for route in ("1145", "1098", "100", "102"):
            self.assertIn(route, error)

    # 1. the gate refuses at the shared write boundary
    def test_unticked_gate_cannot_save_or_enqueue(self) -> None:
        result = self.run_node("direct-unsafe")
        self.assert_blocked(str(result["error"]))
        self.assertEqual(result["saved"], 0)
        self.assertEqual(result["queued"], 0)

    def test_referral_kind_argument_cannot_bypass_gate_with_untyped_record(self) -> None:
        result = self.run_node("direct-unsafe-untyped")
        self.assert_blocked(str(result["error"]))
        self.assertEqual(result["saved"], 0)
        self.assertEqual(result["queued"], 0)

    # 2. a ticked gate saves and queues exactly as before
    def test_ticked_gate_saves_and_queues(self) -> None:
        result = self.run_node("direct-safe")
        self.assertEqual(result["error"], "")
        self.assertEqual(result["saved"], 1)
        self.assertEqual(result["queued"], 1)

    def test_ticked_referral_kind_argument_still_saves_untyped_record(self) -> None:
        result = self.run_node("direct-safe-untyped")
        self.assertEqual(result["error"], "")
        self.assertEqual(result["saved"], 1)
        self.assertEqual(result["queued"], 1)

    # 3a. the queue API refuses an unsafe referral directly, with no write
    def test_queue_api_rejects_unticked_referral(self) -> None:
        result = self.run_node("queue-unsafe")
        self.assert_blocked(str(result["error"]))
        self.assertEqual(result["queued"], 0)

    def test_queue_gate_is_independent_when_write_layer_is_absent(self) -> None:
        result = self.run_node("queue-unsafe-no-l1")
        self.assert_blocked(str(result["error"]))
        self.assertEqual(result["queued"], 0)

    def test_queue_rejects_untyped_record_instead_of_guessing_it_is_safe(self) -> None:
        result = self.run_node("queue-unsafe-untyped")
        self.assertIn("record kind is missing", str(result["error"]))
        self.assertEqual(result["queued"], 0)

    def test_queue_api_still_accepts_a_ticked_referral(self) -> None:
        result = self.run_node("queue-safe")
        self.assertEqual(result["error"], "")
        self.assertEqual(result["queued"], 1)

    # 3b. a legacy queue entry is dropped on retry, never transmitted
    def test_retry_drops_legacy_unsafe_queue_entry_without_transmitting(self) -> None:
        result = self.run_node("retry-unsafe")
        self.assertEqual(result["queued"], 0)
        self.assertEqual(result["pending"], 0)

    def test_retry_drops_untyped_legacy_queue_entry_without_transmitting(self) -> None:
        result = self.run_node("retry-unsafe-untyped")
        self.assertEqual(result["queued"], 0)
        self.assertEqual(result["pending"], 0)

    # 3c. a reopened, previously saved unsafe record cannot be re-saved/queued
    def test_reopened_unsafe_record_cannot_be_resaved_or_queued(self) -> None:
        result = self.run_node("reopened-unsafe")
        self.assert_blocked(str(result["error"]))
        self.assertEqual(result["saved"], 1)   # the old record still exists, unchanged
        self.assertEqual(result["queued"], 0)

    def test_reopened_ticked_record_still_saves(self) -> None:
        result = self.run_node("reopened-safe")
        self.assertEqual(result["error"], "")
        self.assertEqual(result["saved"], 2)

    # no collateral: other forms are untouched by the gate
    def test_non_referral_forms_are_unaffected(self) -> None:
        result = self.run_node("non-referral-unaffected")
        self.assertEqual(result["error"], "")
        self.assertEqual(result["saved"], 1)

    # 2 (surface). the refusal is a blocking, bilingual panel on the page
    def test_form_has_a_bilingual_blocking_error_surface(self) -> None:
        source = REFERRAL_PATH.read_text(encoding="utf-8")
        self.assertIn('id="safeguardingBlock"', source)
        self.assertIn('role="alertdialog"', source)
        self.assertIn("Do not record this case here", source)
        self.assertIn("यहाँ अभिलेख नगर्नुहोस्", source)
        for route in ("1145", "1098", "100", "102", "16600102005"):
            self.assertIn(route, source)
        # the checkbox wording itself is unchanged
        self.assertIn("This is not a GBV case, not an unaccompanied or separated child, and not an immediate risk to life", source)
        self.assertIn("If you cannot tick this, close the form and use the specialised pathway.", source)


if __name__ == "__main__":
    unittest.main()
