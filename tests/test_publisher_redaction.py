#!/usr/bin/env python3
"""Failing-first regression for the LAYER 3 PUBLISHING PATH.

Two bounded outcomes are asserted here, against the REAL files in a real
JavaScript engine:

  A. A demonstration / review document can never reach the collection the
     public website reads. One staged publish is enough to plant a switched-off
     safety floor in that collection, and every later publish inherits it.

  B. Redaction is computed for the WHOLE document before any value is emitted,
     so no channel in the audit finding leaves a below-floor value
     reconstructable.

Real files driven (both are production source, unchanged by this test):
  apps/hub/assets/fb.js               the only writer to `public_stats`
  apps/public/assets/public-read.js   the renderer the public page uses

Synthetic fixtures only. No network. The stubbed Firebase API records calls; it
does not send anything.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FB_PATH = ROOT / "apps" / "hub" / "assets" / "fb.js"
READER_PATH = ROOT / "apps" / "public" / "assets" / "public-read.js"
I18N_STRINGS_PATH = ROOT / "apps" / "public" / "assets" / "i18n-strings.js"

# Loads both real files into one VM context and reports:
#   hasPrepare    - does the publisher expose an analysis-wide prepare step?
#   prepared      - {collection, body} the publisher would emit for the public
#                   shelf, or null when it exposes no such step
#   publishWrites - the collection+id of every write the real publish() makes
#   publishError  - the refusal message, if publish() refused
#   html          - the HTML the public renderer draws from the EMITTED body
#   htmlRaw       - the HTML the public renderer draws from the RAW body
# Kept in the test file so the asserted behaviour is runtime behaviour, not a
# copy of the code.
NODE_HARNESS = r"""
const fs = require("fs");
const vm = require("vm");

const writes = [];
const api = {
  doc(_db, collection, id) { return { collection, id }; },
  setDoc(ref, body) { writes.push({ collection: ref.collection, id: ref.id, body }); return Promise.resolve(); },
  getFirestore() { return {}; },
  serverTimestamp() { return "SERVER_TIME"; },
  getDoc() { return Promise.resolve({ exists() { return false; } }); },
  collection() { return {}; }, query() { return {}; }, where() { return {}; },
  orderBy() { return {}; }, limit() { return {}; },
  onSnapshot() { return function () {}; },
  getDocs() { return Promise.resolve({ forEach() {} }); },
  deleteDoc() { return Promise.resolve(); },
  signIn() { return Promise.resolve(); }, signOut() { return Promise.resolve(); },
  onAuth(_auth, cb) { cb({ email: "reviewer@example.invalid", uid: "u1" }); },
  sendLink() { return Promise.resolve(); }, isLink() { return false; },
  signInLink() { return Promise.resolve(); }
};

function stubEl() {
  return {
    className: "", innerHTML: "", textContent: "", style: {},
    attributes: {},
    appendChild() {}, insertBefore() {}, removeChild() {}, parentNode: null,
    setAttribute(k, v) { this.attributes[k] = String(v); },
    getAttribute(k) { return k in this.attributes ? this.attributes[k] : null; },
    hasAttribute(k) { return k in this.attributes; },
    removeAttribute(k) { delete this.attributes[k]; },
    classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } },
    querySelector() { return null; }, querySelectorAll() { return []; }
  };
}

const localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
const sessionStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
const document = {
  title: "test", readyState: "complete",
  documentElement: stubEl(),
  head: stubEl(), body: Object.assign(stubEl(), { firstElementChild: null }),
  createElement() { return stubEl(); }, getElementById() { return null; },
  addEventListener() {}, querySelectorAll() { return []; }, dispatchEvent() {}
};
const window = {
  FB_CONFIG: { projectId: "test", apiKey: "test" },
  FB_COLLECTION: "submissions",
  addEventListener() {}, history: { replaceState() {} },
  location: { href: "http://test/hub/", pathname: "/hub/", search: "", origin: "http://test" },
  prompt() { return ""; }
};
const context = {
  window, document, localStorage, sessionStorage, console, Promise, Date, JSON, Math, Array, Object,
  setTimeout, clearTimeout, isFinite, String, Number, parseFloat, parseInt, RegExp,
  URLSearchParams: class { get() { return null; } },
  navigator: { onLine: false, language: "en" },
  CustomEvent: function (name) { this.type = name; }
};
window.window = window; window.document = document; window.localStorage = localStorage;
window.sessionStorage = sessionStorage;
context.globalThis = context;
const vmContext = vm.createContext(context);

async function makeModule(code) {
  const m = new vm.SourceTextModule(code, { context: vmContext });
  await m.link(async () => { throw new Error("no nested imports in a stub"); });
  await m.evaluate();
  return m;
}
const APP_SRC = "export function initializeApp(){return {};}\n" +
                "export function getApp(){return {};}\n" +
                "export function getApps(){return [];}";
const FS_SRC = [
  "export const getFirestore = (...a)=>globalThis.__api.getFirestore(...a);",
  "export const doc = (...a)=>globalThis.__api.doc(...a);",
  "export const setDoc = (...a)=>globalThis.__api.setDoc(...a);",
  "export const serverTimestamp = (...a)=>globalThis.__api.serverTimestamp(...a);",
  "export const getDoc = (...a)=>globalThis.__api.getDoc(...a);",
  "export const getDocs = (...a)=>globalThis.__api.getDocs(...a);",
  "export const collection = (...a)=>globalThis.__api.collection(...a);",
  "export const query = (...a)=>globalThis.__api.query(...a);",
  "export const where = (...a)=>globalThis.__api.where(...a);",
  "export const orderBy = (...a)=>globalThis.__api.orderBy(...a);",
  "export const limit = (...a)=>globalThis.__api.limit(...a);",
  "export const onSnapshot = (...a)=>globalThis.__api.onSnapshot(...a);",
  "export const deleteDoc = (...a)=>globalThis.__api.deleteDoc(...a);"
].join("\n");
const AU_SRC = [
  "export const getAuth = ()=>({});",
  "export const signInWithEmailAndPassword = (...a)=>globalThis.__api.signIn(...a);",
  "export const signOut = (...a)=>globalThis.__api.signOut(...a);",
  "export const onAuthStateChanged = (...a)=>globalThis.__api.onAuth(...a);",
  "export const sendSignInLinkToEmail = (...a)=>globalThis.__api.sendLink(...a);",
  "export const isSignInWithEmailLink = (...a)=>globalThis.__api.isLink(...a);",
  "export const signInWithEmailLink = (...a)=>globalThis.__api.signInLink(...a);"
].join("\n");
context.__api = api;

(async () => {
  const appMod = await makeModule(APP_SRC);
  const fsMod = await makeModule(FS_SRC);
  const auMod = await makeModule(AU_SRC);
  context.importModuleDynamically = async function (specifier) {
    if (specifier.endsWith("firebase-app.js")) return appMod;
    if (specifier.endsWith("firebase-firestore.js")) return fsMod;
    if (specifier.endsWith("firebase-auth.js")) return auMod;
    throw new Error("unexpected import: " + specifier);
  };

  // the real bilingual dictionary, and a faithful I18N.t over it, so the page
  // renders real prose. public-read.js falls back to printing the KEY when
  // I18N is absent, which would make every text assertion vacuous; and the real
  // engine is a DOM-heavy bundle this page does not need for the render test.
  const i18nPaths = process.argv.slice(6);
  for (const p of i18nPaths) {
    if (p) vm.runInContext(fs.readFileSync(p, "utf8"), vmContext, { filename: p });
  }
  const strings = window.I18N_STRINGS || {};
  window.I18N = {
    t: function (key, vars) {
      var s = (strings.en || {})[key];
      s = s == null ? "" : String(s);
      if (vars) Object.keys(vars).forEach(function (k) {
        s = s.replace(new RegExp("\\{" + k + "\\}", "g"), vars[k]);
      });
      return s;
    },
    lang: function () { return "en"; }
  };

  const script = new vm.Script(fs.readFileSync(process.argv[1], "utf8"),
    { filename: "fb.js", importModuleDynamically: context.importModuleDynamically });
  script.runInContext(vmContext);

  // wait for the async init to settle
  for (let i = 0; i < 100 && !window.FB.status().ready; i++) {
    await new Promise((r) => setTimeout(r, 20));
  }

  vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), vmContext, { filename: "public-read.js" });

  const docId = process.argv[3];
  const raw = JSON.parse(process.argv[4]);
  const kind = process.argv[5] || "flood";
  const out = { hasPrepare: typeof window.FB.preparePublicRelease === "function" };

  // the public renderer, drawing a body it is handed (no network)
  function draw(body) {
    if (!body) return "";
    const host = stubEl();
    try {
      window.PUBLIC_STATS.preview(
        { state: stubEl(), body: host, panel: stubEl(), kind: kind }, body);
    } catch (e) { return "RENDER_ERROR: " + String((e && e.message) || e); }
    return host.innerHTML;
  }

  // 1. the publisher's own preview of what it would emit
  let prepared = null, refuse = "";
  if (out.hasPrepare) {
    const prep = window.FB.preparePublicRelease(docId, raw);
    if (!prep) refuse = "no result";
    else if (prep.refused) refuse = String(prep.reason || "refused");
    else prepared = { collection: prep.collection, body: prep.body };
  }
  out.refused = refuse;
  out.prepared = prepared;

  // 2. the real write path
  let publishError = "";
  try { await window.FB.publish(docId, raw); }
  catch (e) { publishError = String((e && e.message) || e); }
  out.publishError = publishError;
  out.publishWrites = writes.map((w) => ({ collection: w.collection, id: w.id }));
  out.publishBodies = writes.filter((w) => w.collection === "public_stats").map((w) => w.body);

  // 3. what the page draws from the emitted body, and from the raw body
  out.html = draw(prepared ? prepared.body : raw);
  out.htmlRaw = draw(raw);

  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""

STARTED = {"ready": False}


def run(doc_id: str, raw: dict, kind: str = "flood") -> dict:
    completed = subprocess.run(
        ["node", "--experimental-vm-modules", "-e", NODE_HARNESS,
         str(FB_PATH), str(READER_PATH), doc_id, json.dumps(raw), kind,
         str(I18N_STRINGS_PATH)],
        capture_output=True, text=True, check=True, cwd=str(ROOT),
    )
    return json.loads(completed.stdout)


# The audit's own minimal case, as a healthy-intent publisher would emit it:
# total 100, one visible component 94, the complementary cell 6 hidden.
PUBLISHED_LEAK = {
    "schema": 1,
    "mode": "published",
    "suppressed_below": 10,
    "basis": "synthetic",
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

# What the Hub stamps today: demonstration mode with the safety floor switched
# off, straight at the collection the public reads.
DEMO = {
    "schema": 1,
    "mode": "demonstration",
    "suppressed_below": 1,
    "basis": "synthetic",
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

# The leakage channels named in the finding, read off a rendered page.
CHANNELS = (
    "complement_arithmetic", "suppressed_row_present", "category_label_present",
    "threshold_text_present", "zero_width_bar_present", "raw_max_used",
    "organisation_bypass", "palika_bypass", "declared_floor_defeats_default",
)

_STRUCTURAL_KEYS = {"schema", "schema_version", "suppressed_below", "period_from", "period_to", "codes_version"}


def below_floor_numbers(value, floor=10):
    """Every count below the floor that survives anywhere in a document.

    Structural keys (schema version, the declared floor, dates) are skipped: the
    finding is about counts about people, not about bookkeeping integers."""
    found = []

    def walk(node, path, key):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}", k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]", key)
        elif isinstance(node, bool) or node is None:
            return
        elif isinstance(node, int):
            if key in _STRUCTURAL_KEYS:
                return
            if 0 < node < floor:
                found.append((path, node))

    walk(value, "$", None)
    return found


def visible_integers(html: str, floor=10):
    """Integers a reader can literally read as page text.

    Markup and attributes are stripped first, so a CSS bar width (width:100%)
    is not mistaken for a published figure."""
    import re
    text = re.sub(r"<[^>]*>", " ", html)
    out = []
    for token in re.findall(r"\d[\d,]*", text):
        out.append(int(token.replace(",", "")))
    return out


class PublishingPathTests(unittest.TestCase):
    # =====================================================================
    # A. demonstration / staged publishing must not reach the public collection
    # =====================================================================

    def test_demonstration_document_cannot_reach_the_public_collection(self) -> None:
        result = run("flood_response", DEMO)
        collections = [w["collection"] for w in result["publishWrites"]]
        self.assertNotIn(
            "public_stats", collections,
            "a demonstration document was written to the collection the public reads")

    def test_no_public_write_carries_suppression_disabled(self) -> None:
        result = run("flood_response", DEMO)
        for body in result["publishBodies"]:
            self.assertNotEqual(body.get("mode"), "demonstration",
                                "a public document is still stamped demonstration")
            declared = body.get("suppressed_below")
            if declared is not None:
                self.assertGreaterEqual(declared, 10,
                                        "a public document declares a floor below the policy floor")

    def test_a_published_document_still_reaches_the_public_collection_and_is_redacted(self) -> None:
        result = run("flood_response", PUBLISHED_LEAK)
        collections = [w["collection"] for w in result["publishWrites"]]
        self.assertIn("public_stats", collections,
                      "the real published surface must keep working")
        self.assertEqual(result["publishError"], "")
        for body in result["publishBodies"]:
            self.assertGreaterEqual(body.get("suppressed_below", 0), 10)

    def test_referral_directory_does_not_reach_the_public_aggregate(self) -> None:
        result = run("referral_directory", {
            "schema": 1, "mode": "published", "suppressed_below": 10, "basis": "synthetic",
            "rows": [{"district": "RAS", "palika": "Somewhere", "org": "X",
                      "org_name": "Org X", "activities": ["CNS-I"], "last_report": "2026-09-01"}],
        }, kind="referral")
        collections = [w["collection"] for w in result["publishWrites"]]
        self.assertNotIn("public_stats", collections,
                         "referral content reached the public aggregate")

    def test_an_unrecognised_public_document_fails_closed(self) -> None:
        result = run("something_new", {"schema": 1, "mode": "published", "basis": "x",
                                       "suppressed_below": 10, "contacts": 500})
        collections = [w["collection"] for w in result["publishWrites"]]
        self.assertNotIn("public_stats", collections,
                         "an unrecognised document reached the public collection")

    # =====================================================================
    # B. analysis-wide redaction, channel by channel
    # =====================================================================

    def _emitted(self, doc=PUBLISHED_LEAK, doc_id="flood_response", kind="flood") -> dict:
        result = run(doc_id, doc, kind=kind)
        body = result["prepared"]["body"] if result["prepared"] else dict(doc)
        return {"result": result, "body": body}

    def test_no_below_floor_value_survives_anywhere_in_the_emitted_document(self) -> None:
        emitted = self._emitted()
        self.assertEqual(
            below_floor_numbers(emitted["body"]), [],
            "a below-floor count survived somewhere in the published document")

    def test_complementary_arithmetic_channel_is_closed(self) -> None:
        emitted = self._emitted()
        body = emitted["body"]
        codes = [d.get("code") for d in body.get("districts", [])]
        self.assertNotIn("A", codes, "the below-floor row is still published")
        # with a component withheld, the breakdown's total must be withheld too:
        # 100 - 94 = 6 otherwise
        totals = [body.get("contacts"), body.get("reports")]
        if "A" not in codes and any(d.get("code") == "B" for d in body.get("districts", [])):
            for total in totals:
                self.assertIsNone(
                    total,
                    "a breakdown total was published while one of its components was withheld")

    def test_suppressed_row_and_category_label_are_dropped(self) -> None:
        emitted = self._emitted()
        html = emitted["result"]["html"]
        self.assertNotIn("Alpha", html, "the suppressed category name is still rendered")
        self.assertNotIn("fewer than", html.lower(),
                         "a suppressed row is still rendered as a threshold")

    def test_threshold_text_is_not_used_for_a_suppressed_row(self) -> None:
        emitted = self._emitted()
        self.assertNotIn("fewer than", emitted["result"]["html"].lower())

    def test_bar_geometry_is_computed_from_redacted_values(self) -> None:
        emitted = self._emitted()
        body = emitted["body"]
        fams = {f.get("family"): f.get("contacts") for f in body.get("families", [])}
        self.assertNotIn("small", fams, "the below-floor family is still published")
        html = emitted["result"]["html"].replace(" ", "")
        self.assertNotIn("width:0%", html, "a zero-width bar is still a below-floor tell")

    def test_organisation_and_palika_bypass_is_closed(self) -> None:
        emitted = self._emitted()
        body = emitted["body"]
        for field in ("organisations", "palikas"):
            value = body.get(field)
            if value is not None:
                self.assertGreaterEqual(value, 10,
                                        f"a below-floor {field} count was published")

    def test_declared_floor_cannot_lower_the_policy_floor(self) -> None:
        doc = dict(PUBLISHED_LEAK)
        doc["suppressed_below"] = 1
        emitted = self._emitted(doc)
        self.assertGreaterEqual(emitted["body"].get("suppressed_below", 0), 10,
                                "a document lowered the floor below policy")

    # ---- reader-side defence in depth (the fix must not rely on the publisher
    #      alone, because a raw value already in the collection is exposed to
    #      anyone reading the document directly)

    def test_reader_alone_hides_a_below_floor_value(self) -> None:
        result = run("flood_response", PUBLISHED_LEAK)
        html = result["htmlRaw"]
        self.assertNotIn("fewer than", html.lower(),
                         "the reader still renders a threshold row for a below-floor value")
        self.assertNotIn("Alpha", html, "the reader still renders the suppressed category")
        self.assertNotIn("width:0%", html.replace(" ", ""),
                         "the reader still draws a zero-width below-floor bar")

    def test_reader_reconstruction_is_impossible_from_the_rendered_page(self) -> None:
        result = run("flood_response", PUBLISHED_LEAK)
        html = result["htmlRaw"]
        numbers = visible_integers(html)
        # 100 - 94 = 6 must not be available: a total and its complement cannot
        # both be on the page when the third cell is hidden.
        self.assertFalse(100 in numbers and 94 in numbers,
                         "the published total and its complement are both on the page")
        self.assertNotIn(6, numbers, "the hidden value is readable on the page")


if __name__ == "__main__":
    unittest.main()
