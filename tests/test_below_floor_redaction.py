#!/usr/bin/env python3
"""Failing-first reproduction of the Layer 3 below-floor reconstruction channels.

This drives the REAL files in a real JavaScript engine (Node `vm`):

  apps/hub/assets/fb.js               the only writer to `public_stats`
  apps/public/assets/public-read.js   the renderer the public page uses

It rebuilds the audit's own minimal case (published total 100, one visible
component 94, the complementary cell 6 hidden) and asks two questions:

  A. Is a below-floor count still RECOVERABLE from the document that is written
     to the collection the public reads?
  B. Is a below-floor count still RECOVERABLE from the page that is drawn?

A channel is only closed when a test that failed at base now fails closed.

Synthetic fixtures only. No network, nothing written anywhere: the stubbed
Firebase API records calls, it does not send them.
"""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FB_PATH = ROOT / "apps" / "hub" / "assets" / "fb.js"
READER_PATH = ROOT / "apps" / "public" / "assets" / "public-read.js"
I18N_STRINGS_PATH = ROOT / "apps" / "public" / "assets" / "i18n-strings.js"

# Loads both real files into one VM context and reports:
#   hasPrepare    - does the publisher expose an analysis-wide prepare step?
#   prepared      - {collection, body} the publisher would emit, or null
#   refuseReason  - the refusal, when the prepare step refused outright
#   publishError  - the refusal message, if publish() refused
#   publishWrites - the collection+id of every write the real publish() made
#   publicBodies  - the body of every write the real publish() made to public_stats
#   htmlEmitted   - the page drawn from the emitted body (or the raw body)
#   htmlRaw       - the page drawn from the RAW body, never trusted
#   htmlVariant   - the page drawn from a variant whose WITHHELD values differ
#   readerRedacted- the reader's defence-in-depth redacted document, or null
#   readerError   - the reader's refusal for a shape it cannot safely redact
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
    className: "", innerHTML: "", textContent: "", style: {}, attributes: {},
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
  title: "test", readyState: "complete", documentElement: stubEl(),
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
  window, document, localStorage, sessionStorage, console, Promise, Date, JSON, Math,
  Array, Object, setTimeout, clearTimeout, isFinite, isNaN, String, Number,
  parseFloat, parseInt, RegExp, Error, TypeError, Symbol, Map, Set,
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
  // renders real prose rather than printing the key.
  vm.runInContext(fs.readFileSync(process.argv[6], "utf8"), vmContext, { filename: "i18n-strings.js" });
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

  for (let i = 0; i < 200 && !window.FB.status().ready; i++) {
    await new Promise((r) => setTimeout(r, 10));
  }

  vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), vmContext, { filename: "public-read.js" });

  const docId = process.argv[3];
  const raw = JSON.parse(process.argv[4]);
  const kind = process.argv[5] || "flood";
  const variant = process.argv[7] ? JSON.parse(process.argv[7]) : null;
  const out = { hasPrepare: typeof window.FB.preparePublicRelease === "function" };

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
  out.refuseReason = refuse;
  out.prepared = prepared;

  // 2. the real write path: what actually lands in the collection
  let publishError = "";
  try { await window.FB.publish(docId, raw); }
  catch (e) { publishError = String((e && e.message) || e); }
  out.publishError = publishError;
  out.publishWrites = writes.map((w) => ({ collection: w.collection, id: w.id }));
  out.publicBodies = writes.filter((w) => w.collection === "public_stats").map((w) => w.body);

  // 3. what the page draws from the raw body and from a variant body whose
  //    withheld values are different. If the page depends on a withheld value
  //    (geometry, ordering, a total), these two differ.
  out.htmlRaw = draw(raw);
  out.htmlVariant = variant ? draw(variant) : null;
  out.htmlEmitted = draw(prepared ? prepared.body : raw);
  out.htmlOfWritten = out.publicBodies.length ? draw(out.publicBodies[0]) : null;

  // 4. the reader's redaction result itself. Rendering can hide fields it does
  //    not understand; this checks that the whole document is safe before any
  //    renderer is allowed to select fields from it.
  out.readerRedacted = null;
  out.readerError = "";
  try { out.readerRedacted = window.PUBLIC_STATS.redact(raw); }
  catch (e) { out.readerError = String((e && e.message) || e); }

  // 5. idempotency: redacting an already-redacted body is a no-op, so a
  //    re-publish of what was published cannot change what the page shows.
  if (typeof window.FB.redactPublicBody === "function" && out.publicBodies.length) {
    try {
      var again = window.FB.redactPublicBody(out.publicBodies[0]);
      out.redactIdempotent = JSON.stringify(again) === JSON.stringify(out.publicBodies[0]);
      out.stillLeaks = window.FB.belowFloorCount(again, window.FB.REDACTION_FLOOR, "$");
    } catch (e) { out.redactIdempotent = false; out.stillLeaks = "error: " + e.message; }
  }

  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error((e && e.stack) || e); process.exit(1); });
"""


def run(doc_id: str, raw: dict, kind: str = "flood", variant: dict | None = None) -> dict:
    argv = [
        "node", "--experimental-vm-modules", "-e", NODE_HARNESS,
        str(FB_PATH), str(READER_PATH), doc_id, json.dumps(raw), kind,
        str(I18N_STRINGS_PATH), json.dumps(variant) if variant else "",
    ]
    completed = subprocess.run(argv, capture_output=True, text=True, cwd=str(ROOT))
    if completed.returncode != 0:
        raise AssertionError("harness failed: " + (completed.stderr or completed.stdout))
    return json.loads(completed.stdout)


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

# The audit's own minimal case, as a healthy-intent publisher would emit it:
# total 100, one visible component 94, the complementary cell 6 hidden. The
# floor is the policy floor and the mode is production, so this document is
# NOT refused by the sink guard -- it is the shape that reaches the collection.
PUBLISHED_LEAK = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture: total, one visible complement, one hidden cell",
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

# The same document, but the top-level total differs while every visible figure
# is identical. A page that shows the total (or sizes a bar from it) differs
# between the two; a page that withholds it cannot.
PUBLISHED_LEAK_VARIANT = json.loads(json.dumps(PUBLISHED_LEAK))
PUBLISHED_LEAK_VARIANT["contacts"] = 137
PUBLISHED_LEAK_VARIANT["reports"] = 137

# A document that declares the suppression off. The sink must not write it, and
# the reader must not honour it.
PUBLISHED_LEAK_FLOOR_ONE = json.loads(json.dumps(PUBLISHED_LEAK))
PUBLISHED_LEAK_FLOOR_ONE["suppressed_below"] = 1

# A schema-2 shape: the same error class nested one level deeper.
SCHEMA2_LEAK = {
    "schema": 2,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture, schema two",
    "reports": 100,
    "contacts": 100,
    "organisations_count": 20,
    "palikas_count": 8,
    "sites": [
        {"code": "S1", "name": "Site one", "reports": 6, "contacts": 6, "organisations": ["O1"]},
        {"code": "S2", "name": "Site two", "reports": 94, "contacts": 94, "organisations": ["O2"]},
    ],
    "organisations": [
        {"name": "O1", "reports": 6, "contacts": 6, "sites": 1},
        {"name": "O2", "reports": 94, "contacts": 94, "sites": 20},
    ],
    "activities": [
        {"code": "A1", "name": "Activity one", "reports": 6, "contacts": 6, "organisations": 1},
        {"code": "A2", "name": "Activity two", "reports": 94, "contacts": 94, "organisations": 20},
    ],
    "sadd": {
        "bands": [{"band": "0-4", "f": 3, "m": 2, "o": 0}],
        "total": 100,
        "disaggregated_total": 100,
    },
}

# A document in which every published count is at or above the floor. It must
# still be published -- the redaction must not be a blanket refusal.
CLEAN_DOC = {
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

# A below-floor SCALAR with no row below the floor: the scalar goes, the rows
# stay. This is the narrower-withholding case and it must still fail closed for
# the scalar itself.
SCALAR_LEAK = json.loads(json.dumps(CLEAN_DOC))
SCALAR_LEAK["organisations"] = 4

# A shape this code does not know how to redact: a below-floor count held in a
# numeric array (the matrix rows are published as arrays). The sink must
# REFUSE rather than write it.
UNREDACTABLE = {
    "schema": 2,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture, a count this code cannot redact",
    "matrix": [["Org", "RAS", "Palika", "P0001", "A1", "Activity", 6, 6]],
}

# A nested complementary cell. The enclosing district row carries its own
# total; dropping the nested small row must also withhold that ancestor total,
# or the surviving nested complement reconstructs the hidden value (100-94=6).
NESTED_ROW_LEAK = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture, nested complementary cell",
    "contacts": 100,
    "districts": [
        {
            "code": "A",
            "contacts": 100,
            "breakdown": [
                {"family": "small", "contacts": 6},
                {"family": "large", "contacts": 94},
            ],
        },
    ],
}

# The same complementary arithmetic without a nested row family. The small
# component is a scalar inside a plain object; withholding that scalar must
# propagate to the enclosing district/root totals, or 100 - 94 still reveals 6.
PLAIN_OBJECT_SCALAR_LEAK = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture, scalar nested in a plain object",
    "contacts": 100,
    "districts": [
        {
            "code": "A",
            "contacts": 100,
            "detail": {"small": 6, "large": 94},
        },
    ],
}

# The document declares floor 20, above the page default of 10, so a matrix
# value of 15 is below the EFFECTIVE floor even though it clears the default.
# The unrecognised numeric-array shape must be refused by publisher and reader.
DECLARED_FLOOR_UNREDACTABLE = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 20,
    "basis": "synthetic fixture, declared floor above default",
    "matrix": [["Org", "RAS", "Palika", "P0001", "A1", "Activity", 15, 15]],
}

# Malformed-but-JSON row families. A list containing aggregate row objects and
# non-row members has no safe interpretation: treating it as a non-row list
# leaves category labels and complements beside a covering total, while
# silently filtering the foreign member invents a repair policy. Publisher and
# reader must therefore refuse the whole document.
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

# --- the CLASS, not just the one shape ---------------------------------
# A dropped row taints EVERY ancestor that could hold a total covering it, at
# any depth and through any kind of container. Each of these is the same
# arithmetic (100 - 94 = 6) moved one structure away, and each must fail closed.
_DEEP = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture, three levels of nesting",
    "districts": [
        {
            "code": "A", "contacts": 100,
            "zones": [
                {
                    "zone": "z1", "contacts": 100,
                    "hamlets": [
                        {"hamlet": "h1", "contacts": 6},
                        {"hamlet": "h2", "contacts": 94},
                    ],
                },
            ],
        },
    ],
}
_NONROW_ANCESTOR = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture, non-row object holds the total",
    "districts": [
        {
            "code": "A", "contacts": 100,
            "grid": {
                "total": 100,
                "cells": [
                    {"cell": "c1", "contacts": 6},
                    {"cell": "c2", "contacts": 94},
                ],
            },
        },
    ],
}
_OBJECT_INSIDE_ROW = {
    "schema": 1,
    "mode": "production",
    "suppressed_below": 10,
    "basis": "synthetic fixture, total inside a nested object of a row",
    "districts": [
        {
            "code": "A", "contacts": 100,
            "meta": {
                "total": 100,
                "rows": [
                    {"r": "r1", "contacts": 6},
                    {"r": "r2", "contacts": 94},
                ],
            },
        },
    ],
}

# each fixture and the field paths that must have been withheld
NESTED_CLASS = [
    ("deep", _DEEP, ["districts[0].contacts", "districts[0].zones[0].contacts"]),
    ("non-row ancestor", _NONROW_ANCESTOR, ["districts[0].contacts", "districts[0].grid.total"]),
    ("object inside a row", _OBJECT_INSIDE_ROW, ["districts[0].contacts", "districts[0].meta.total"]),
]


def _at(obj, path):
    """Walk `districts[0].grid.total`-style paths (test-only helper)."""
    node = obj
    for part in path.split("."):
        name = part.split("[")[0]
        if name:
            node = node[name]
        for idx in re.findall(r"\[(\d+)\]", part):
            node = node[int(idx)]
    return node


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

_STRUCTURAL_KEYS = {
    "schema", "schema_version", "suppressed_below", "period_from", "period_to",
    "codes_version",
}


def below_floor_numbers(value, floor: int = 10):
    """Every count below the floor that survives anywhere in a document.

    Structural bookkeeping integers (schema version, the declared floor, dates)
    are skipped: the finding is about counts of people and reports.
    """
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


def visible_integers(html: str):
    """Integers a reader can literally read as page text (markup stripped)."""
    text = re.sub(r"<[^>]*>", " ", html)
    return [int(tok.replace(",", "")) for tok in re.findall(r"\d[\d,]*", text)]


def emitted(result: dict) -> dict | None:
    """The body the publisher actually writes to the public collection.

    At base the publisher writes the raw body, so this is the raw body: that is
    exactly the failing-first condition. After the fix it is the redacted body.
    """
    bodies = result["publicBodies"]
    return bodies[0] if bodies else None


class BelowFloorRedactionTests(unittest.TestCase):
    # ==================================================================
    # A. the PUBLISHER: what is written to the collection the public reads
    # ==================================================================

    def test_no_below_floor_count_survives_in_the_published_document(self) -> None:
        """Whole-document redaction: no below-floor count reaches the shelf."""
        body = emitted(run("flood_response", PUBLISHED_LEAK))
        assert body is not None, "the published surface stopped working entirely"
        self.assertEqual(
            below_floor_numbers(body), [],
            "a below-floor count survived in the document written to public_stats",
        )

    def test_complementary_cell_cannot_be_reconstructed(self) -> None:
        """total 100 - complement 94 = 6 must not be computable."""
        result = run("flood_response", PUBLISHED_LEAK)
        body = emitted(result)
        assert body is not None, "nothing was written to the public collection"
        codes = [d.get("code") for d in body.get("districts", [])]
        self.assertNotIn("A", codes, "the below-floor district row is still published")
        # With a component withheld, the totals it fed cannot be published.
        for total in ("contacts", "reports", "people_reported",
                      "distinct_people_reported"):
            self.assertIsNone(
                body.get(total),
                f"{total} was published while a component of it was withheld: "
                "the hidden cell is recoverable by subtraction",
            )

    def test_suppressed_district_row_and_category_label_are_dropped(self) -> None:
        body = emitted(run("flood_response", PUBLISHED_LEAK))
        assert body is not None, "nothing was written to the public collection"
        blob = json.dumps(body)
        self.assertNotIn("Alpha", blob, "the suppressed category name is still in the document")
        self.assertNotIn("A", [d.get("code") for d in body.get("districts", [])])

    def test_suppressed_family_row_is_dropped(self) -> None:
        body = emitted(run("flood_response", PUBLISHED_LEAK))
        assert body is not None, "nothing was written to the public collection"
        families = {f.get("family") for f in body.get("families", [])}
        self.assertNotIn("small", families, "the below-floor family is still in the document")

    def test_organisation_and_palika_counts_go_through_the_floor(self) -> None:
        """The `num()` bypass: these must pass the same floor as any count."""
        body = emitted(run("flood_response", PUBLISHED_LEAK))
        assert body is not None, "nothing was written to the public collection"
        for field in ("organisations", "palikas"):
            value = body.get(field)
            if value is not None:
                self.assertGreaterEqual(
                    value, 10, f"a below-floor {field} count was published")

    def test_declared_floor_cannot_lower_the_policy_floor(self) -> None:
        result = run("flood_response", PUBLISHED_LEAK_FLOOR_ONE)
        for body in result["publicBodies"]:
            declared = body.get("suppressed_below")
            self.assertGreaterEqual(
                declared, 10, "a document lowered the floor below policy on a public write")

    def test_nested_schema_two_counts_are_redacted_too(self) -> None:
        body = emitted(run("coordination_full", SCHEMA2_LEAK))
        assert body is not None, "nothing was written to the public collection"
        self.assertEqual(
            below_floor_numbers(body), [],
            "a below-floor count survived inside a nested schema-2 breakdown",
        )

    def test_nested_drop_also_withholds_the_enclosing_published_row_total(self) -> None:
        """A dropped nested row taints the totals on every enclosing row, or
        the surviving nested complement reconstructs the hidden value."""
        body = emitted(run("flood_response", NESTED_ROW_LEAK))
        assert body is not None, "nothing was written to the public collection"
        district = body["districts"][0]
        self.assertIsNone(
            district.get("contacts"),
            "the enclosing row total survived its dropped nested component: 100-94=6",
        )
        self.assertEqual(
            [row.get("family") for row in district.get("breakdown", [])],
            ["large"],
        )

    def test_nested_scalar_suppression_taints_every_covering_published_total(self) -> None:
        """A scalar suppressed inside a plain object must taint its enclosing
        objects just like a dropped row; otherwise 100-94 reconstructs 6."""
        body = emitted(run("flood_response", PLAIN_OBJECT_SCALAR_LEAK))
        assert body is not None, "nothing was written to the public collection"
        district = body["districts"][0]
        self.assertIsNone(
            district.get("contacts"),
            "the district total survived a nested scalar suppression: 100-94=6",
        )
        self.assertIsNone(
            body.get("contacts"),
            "the document total survived a nested scalar suppression",
        )
        self.assertIsNone(district["detail"].get("small"))
        self.assertIsNone(
            district["detail"].get("large"),
            "the sibling complement survived beside a suppressed scalar",
        )

    # --- the redaction must not be a blanket refusal -----------------------

    def test_a_clean_document_is_still_published_unchanged(self) -> None:
        body = emitted(run("flood_response", CLEAN_DOC))
        assert body is not None, "a clean document was refused, so the surface is broken"
        for key in ("reports", "contacts", "organisations", "palikas"):
            self.assertEqual(body.get(key), CLEAN_DOC[key], f"{key} was withheld needlessly")
        self.assertEqual(len(body.get("districts", [])), 2)
        self.assertEqual(len(body.get("families", [])), 2)

    def test_a_below_floor_scalar_is_withheld_while_clean_rows_survive(self) -> None:
        """The narrower case: nothing is a row-level leak, so only the scalar
        below the floor is withheld and the rows stay."""
        body = emitted(run("flood_response", SCALAR_LEAK))
        assert body is not None, "the document was refused instead of redacted"
        self.assertIsNone(body.get("organisations"),
                          "a below-floor scalar count was published")
        self.assertEqual(len(body.get("districts", [])), 2,
                         "clean rows were dropped for a scalar-only leak")

    def test_a_shape_that_cannot_be_redacted_is_refused_not_written(self) -> None:
        """Fail closed: a below-floor count this code does not recognise (here
        a numeric array, the matrix shape) must stop the write entirely."""
        result = run("coordination_full", UNREDACTABLE)
        self.assertEqual(result["publishWrites"], [],
                         "a document with an unredactable below-floor count was written")
        self.assertIn("below-floor", result["publishError"])

    def test_publisher_verifies_against_the_effective_declared_floor(self) -> None:
        """A document declaring floor 20 makes 15 below-floor. Verification
        must use the effective floor, not the 10 default, or the value is
        written and the reader is the only thing left holding the line."""
        result = run("flood_response", DECLARED_FLOOR_UNREDACTABLE)
        self.assertEqual(
            result["publishWrites"], [],
            "a value below the document's effective floor was written because "
            "verification used the default floor",
        )
        self.assertIn("below-floor", result["publishError"])

    def test_publisher_refuses_mixed_row_families_without_writing(self) -> None:
        """An aggregate row family mixed with null/a primitive is malformed,
        not a non-row array. It must produce zero public writes rather than
        retain category `small` and complement 94 beside total 100."""
        for label, families in MIXED_ROW_FAMILIES:
            with self.subTest(shape=label):
                result = run("flood_response", mixed_row_document(families))
                self.assertEqual(
                    result["publishWrites"], [],
                    f"{label}: a malformed mixed row family reached public_stats",
                )
                self.assertIn("mixed row family", result["publishError"].lower())

    def test_the_whole_ancestor_class_is_withheld_not_one_shape(self) -> None:
        """The defect class, not the reported shape: a dropped row must taint
        every ancestor that could carry a covering total, at any depth and
        through any container -- not only the row that directly enclosed it."""
        for label, doc, paths in NESTED_CLASS:
            with self.subTest(shape=label):
                body = emitted(run("flood_response", doc))
                assert body is not None, f"{label}: nothing was written"
                for path in paths:
                    with self.subTest(path=path):
                        self.assertIsNone(
                            _at(body, path),
                            f"{label}: {path} still published a total that covered "
                            "the dropped row, so the hidden cell is recoverable",
                        )
                self.assertEqual(below_floor_numbers(body), [])

    def test_redaction_of_an_already_redacted_document_is_a_no_op(self) -> None:
        result = run("flood_response", PUBLISHED_LEAK)
        self.assertTrue(result.get("redactIdempotent"),
                        "re-redacting a published document changed it")
        self.assertEqual(result.get("stillLeaks"), "",
                         "a below-floor count survives the redaction pass")

    # ==================================================================
    # B. the READER: what the page SHOWS, from a raw document
    # ==================================================================

    def test_reader_drops_the_suppressed_row_and_its_label(self) -> None:
        html = run("flood_response", PUBLISHED_LEAK)["htmlRaw"]
        self.assertNotIn("Alpha", html, "the reader still draws the suppressed category")
        self.assertNotIn("fewer than", html.lower(),
                         "the reader still draws a threshold row for a hidden cell")

    def test_reader_draws_no_zero_width_bar(self) -> None:
        html = run("flood_response", PUBLISHED_LEAK)["htmlRaw"].replace(" ", "")
        self.assertNotIn("width:0%", html, "a zero-width bar is still a below-floor tell")

    def test_reader_page_cannot_reconstruct_the_hidden_value(self) -> None:
        html = run("flood_response", PUBLISHED_LEAK)["htmlRaw"]
        numbers = visible_integers(html)
        self.assertNotIn(6, numbers, "the hidden value is readable on the page")
        self.assertFalse(
            100 in numbers and 94 in numbers,
            "the published total and its complement are both readable, so 100-94=6",
        )

    def test_reader_does_not_use_a_withheld_value_in_geometry(self) -> None:
        """The page must not depend on a value it has hidden.

        Two documents identical in every VISIBLE figure but differing in the
        withheld total must render identically once nothing withheld is used.
        """
        a = run("flood_response", PUBLISHED_LEAK)["htmlRaw"]
        b = run("flood_response", PUBLISHED_LEAK_VARIANT)["htmlRaw"]
        self.assertEqual(
            a, b,
            "the drawn page changes when a withheld value changes: it is used in "
            "geometry, a total or ordering",
        )

    def test_reader_ignores_a_declared_floor_below_policy(self) -> None:
        html = run("flood_response", PUBLISHED_LEAK_FLOOR_ONE)["htmlRaw"]
        self.assertNotIn("Alpha", html)
        self.assertNotIn(6, visible_integers(html), "a declared floor of 1 unmasked the value")
        self.assertNotIn("fewer than", html.lower())

    def test_reader_withholds_the_enclosing_total_after_a_nested_drop(self) -> None:
        """The reader must apply the SAME whole-document rule: a dropped nested
        row withholds the ancestor total, so 100-94 does not yield the cell."""
        result = run("flood_response", NESTED_ROW_LEAK)
        body = result["readerRedacted"]
        assert body is not None, result["readerError"] or "reader returned no redacted document"
        district = body["districts"][0]
        self.assertIsNone(
            district.get("contacts"),
            "the reader kept an enclosing total whose nested component it dropped",
        )
        blob = json.dumps(body)
        self.assertNotIn("small", blob)

    def test_reader_propagates_nested_scalar_suppression_to_covering_totals(self) -> None:
        """The reader must repeat the publisher's scalar-taint propagation for
        raw documents written by an older or foreign publisher."""
        result = run("flood_response", PLAIN_OBJECT_SCALAR_LEAK)
        body = result["readerRedacted"]
        assert body is not None, result["readerError"] or "reader returned no redacted document"
        district = body["districts"][0]
        self.assertIsNone(
            district.get("contacts"),
            "the reader kept a district total covering a suppressed nested scalar",
        )
        self.assertIsNone(
            body.get("contacts"),
            "the reader kept a document total covering a suppressed nested scalar",
        )
        self.assertIsNone(district["detail"].get("small"))
        self.assertIsNone(
            district["detail"].get("large"),
            "the reader kept the sibling complement beside a suppressed scalar",
        )

    def test_reader_refuses_against_the_effective_declared_floor(self) -> None:
        result = run("flood_response", DECLARED_FLOOR_UNREDACTABLE)
        self.assertIsNone(
            result["readerRedacted"],
            "the reader retained a value below the document's declared floor",
        )
        self.assertIn("below-floor", result["readerError"])

    def test_reader_refuses_mixed_row_families(self) -> None:
        """The defence-in-depth reader must reject the same malformed arrays;
        it may not return a partly redacted body for the renderer to crash on."""
        for label, families in MIXED_ROW_FAMILIES:
            with self.subTest(shape=label):
                result = run("flood_response", mixed_row_document(families))
                self.assertIsNone(
                    result["readerRedacted"],
                    f"{label}: reader accepted a malformed mixed row family",
                )
                self.assertIn("mixed row family", result["readerError"].lower())

    def test_reader_withholds_the_whole_ancestor_class_too(self) -> None:
        """The reader, not only the publisher, must withhold every ancestor of
        a dropped row -- otherwise a document written by an older or foreign
        publisher still yields 100-94 on this page."""
        for label, doc, paths in NESTED_CLASS:
            with self.subTest(shape=label):
                result = run("flood_response", doc)
                body = result["readerRedacted"]
                assert body is not None, result["readerError"] or f"{label}: no redacted doc"
                for path in paths:
                    with self.subTest(path=path):
                        self.assertIsNone(
                            _at(body, path),
                            f"{label}: the reader kept {path}, a total covering the "
                            "row it dropped",
                        )

    def test_page_drawn_from_the_written_document_matches_the_raw_document(self) -> None:
        """Redaction is idempotent: redacting what was already redacted is a
        no-op, so the page cannot change if the document is re-published."""
        result = run("flood_response", PUBLISHED_LEAK)
        written = result["htmlOfWritten"]
        raw_page = result["htmlRaw"]
        assert written is not None, "nothing was written, so the page cannot be checked"
        self.assertEqual(
            written, raw_page,
            "the page drawn from the published (redacted) document differs from the "
            "page drawn from the raw document: some withheld value still shows",
        )


if __name__ == "__main__":
    unittest.main()
