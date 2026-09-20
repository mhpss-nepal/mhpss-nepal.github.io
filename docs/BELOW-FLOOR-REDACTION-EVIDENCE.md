# Below-floor redaction, computed once per document

Task `t_f3b83790` — *Fix: compute below-floor redaction once per document, not per number*.
Tenant `mhpss-nepal` · branch `architecture/v2-immutable-authority` (review artifact, **not deployed**).

| Field | Value |
|---|---|
| Worktree | `/root/mhpss-nepal-work/v2-authority-redesign` — sole task on it (checked before starting) |
| Base (parent of the test commit) | `775e142c2a37324bb74af9d58cf880f626174367` |
| Test-only commits (red) | `04af6d7` (core channels), `b96303c` (browser + fail-closed + clean + idempotency + nested) |
| Head (fix, green) | `a3b3a218171886f4fef17d4e1a6c0f6e46dc98bb` |
| Production refs | public `68bf197`, form `9032bb7`, hub `ff2d4e2` — **unchanged**; no push / PR / merge / deploy |
| Worktree after the fix | clean |
| Status | **DONE - REVIEW ARTIFACT** with open questions for Adib (§6) |

Synthetic fixtures only. No Publish was pressed, nothing was written to `public_stats` or
any other collection, and the live check was read-only and aggregate-only.

---

## 1. The outcome

> Redaction is computed **once for the whole document, before any value is emitted**, at the
> **publisher**. A suppressed cell cannot be recovered by subtracting the published parts from a
> published total; a suppressed **row** is dropped rather than labelled; organisation/palika
> counts go through the **same** floor; and the drawn geometry is a function of redacted values
> only.

The fix is on the **publisher** (`apps/hub/assets/fb.js`), because a raw value already written to
`public_stats` is exposed to anyone who reads the document directly. The **reader**
(`apps/public/assets/public-read.js`) computes the *same* decision as defence in depth, so this
site cannot be the place that reveals it either.

## 2. What was reproduced first (failing-first)

`tests/test_below_floor_redaction.py` drives the **real** publisher and the **real** reader in a
JavaScript engine (Node `vm`). It rebuilds the audit's own minimal case — published total 100, one
visible component 94, the complementary cell 6 hidden — and reads a below-floor count back out of
the document that is written, and off the page that is drawn.

At **base**, on the same test, before the fix (exact command and output):

```text
$ python3 -m unittest tests.test_below_floor_redaction
Ran 17 tests in 1.506s
FAILED (failures=13)
```

The 13 that failed at base are every channel named in the finding, each one a real reconstruction:

| Channel | The base test that failed, and what it showed |
|---|---|
| Complementary-cell arithmetic | `test_complementary_cell_cannot_be_reconstructed`, `test_no_below_floor_count_survives...` — district A (`{contacts: 6}`) was written to `public_stats` unchanged; `100 − 94 = 6` |
| Row presence | `test_suppressed_family_row_is_dropped` — family `small` was still a published row |
| Category label | `test_suppressed_district_row_and_category_label_are_dropped` — district A and its name were published |
| Threshold text | `test_reader_drops_the_suppressed_row_and_its_label` — the page drew `fewer than 10` |
| Zero-width bar | `test_reader_draws_no_zero_width_bar` — a below-floor family drew a `width:0%` bar |
| `max` over raw values | `test_reader_does_not_use_a_withheld_value_in_geometry` — the drawn page changed when a *withheld* total changed, i.e. geometry depended on hidden values |
| Organisation/palika bypass | `test_organisation_and_palika_counts_go_through_the_floor` — a count of 8 was drawn unsuppressed |
| Declared floor defeats default | `test_declared_floor_cannot_lower_the_policy_floor`, `test_reader_ignores_a_declared_floor_below_policy` — `suppressed_below: 1` rendered 6 as itself |
| Nested schema-2 breakdown | `test_nested_schema_two_counts_are_redacted_too` — below-floor counts inside `sites`/`organisations`/`activities` survived |
| No fail-closed refusal | `test_a_shape_that_cannot_be_redacted_is_refused_not_written` — a below-floor count in an unreckoned shape was still written |
| Scalar-only leak | `test_a_below_floor_scalar_is_withheld_while_clean_rows_survive` — a lone below-floor scalar was published |
| Redaction not idempotent | `test_redaction_of_an_already_redacted_document_is_a_no_op` — there was no redaction pass to be a no-op |

`tests/test_below_floor_redaction_browser.py` is the **real-browser** half (the task's warning: a
passing suite is not evidence the page works). It has two tests: what the public page SHOWS for a
below-floor document, and that the Hub preview computes what would actually be written. At base, in
headless Chromium on the real public page with its real CSS and i18n:

```text
$ python3 -m unittest tests.test_below_floor_redaction_browser
FAIL: test_the_real_page_hides_a_below_floor_value
AssertionError: 'small' unexpectedly found in
'100 … small / fewer than 10 / large / 94 … A / fewer than 10 / fewer than 10 / 1 / B / 94 / 99 / 20'
FAIL: test_hub_preview_shows_the_redacted_document
AssertionError: the Hub cannot compute what would be written
```

The page showed the total 100, the complement 94, and district A as `fewer than 10`: `100 − 94 = 6`.

### The original reproduction, re-run

The audit's reproduction was run first, unchanged, and still reveals the value (its own test
asserts the leak):

```text
$ python3 coordination/evidence/layer3-below-floor-reconstruction/mhpss_public_aggregate_privacy_demo.py
{ "reconstructed_hidden_value": 6, "small_family_bar_width_percent": 0, ... }
$ python3 coordination/evidence/layer3-below-floor-reconstruction/test_mhpss_public_aggregate_privacy_demo.py
Ran 2 tests … OK
```

That file models the *old* per-number logic and is deliberately **not** updated by this ticket —
the task says the fixed code must make *that exact reproduction* fail to reveal the value. The
link is `tests/test_below_floor_redaction.py`: it feeds the same fixture (`100 / 94 / 6`) through
the **real** publisher and computes the document that would actually be written. After the fix the
hidden `6` is not written and not drawable, so the reproduction's arithmetic has nothing to
subtract. The evidence doc of the sibling ticket (`docs/PUBLICATION-PRIVACY-GUARD-EVIDENCE.md`)
covers the separate question of whether such a document could reach the collection at all.

## 3. What now, after the fix

```text
$ python3 -m unittest tests.test_below_floor_redaction -v
Ran 17 tests in 1.581s

OK

$ python3 -m unittest tests.test_below_floor_redaction_browser -v
Ran 2 tests in 3.439s

OK
```

The same leaking document, through the real publisher, is written as (abridged):

```json
{ "schema": 1, "mode": "production", "suppressed_below": 10,
  "reports": null, "contacts": null, "organisations": null, "palikas": null,
  "districts": [ {"code": "B", "name": "Bravo", "reports": 99, "contacts": 94, "organisations": 20} ],
  "families":  [ {"family": "large", "contacts": 94} ] }
```

The below-floor district and family are gone; the totals they fed are withheld (`null`); district
B's own figures are above the floor and stay. On the real page a reader sees only district B and
family `large`; the string `fewer than` never appears, there is no zero-width bar, and the drawn
page is identical when the withheld total is changed.

## 4. Channels closed

Every row is a **verified** result: the claim is checked by the Node test on the real files, and
the rendered-page claims re-checked in a real Chromium.

| # | Channel (from the finding) | Before | After |
|---|---|---|---|
| 1 | Complementary-cell arithmetic | `100 − 94 = 6` recoverable | the below-floor row is dropped **and** every total it fed is withheld |
| 2 | Suppressed row presence | row kept, shown as `fewer than 10` | row dropped whole |
| 3 | Category label | the category name is drawn | the category does not appear on the page |
| 4 | Threshold text as a tell | `fewer than 10` rendered | no threshold phrase is rendered for a dropped row |
| 5 | Zero-width bar | a small family drew a `0`-width bar | the row is gone; no zero-width bar is drawn |
| 6 | `max` over raw values | the bar scale included suppressed values | the scale is computed over the rows actually drawn; the page is byte-identical when a withheld value changes |
| 7 | Organisation / palika bypass | rendered via `num()`, no floor | both go through `safe()`, the same floor |
| 8 | Declared floor defeats the default | `suppressed_below: 1` unmasked the value | publisher and reader both floor at the policy floor (10); the Hub no longer declares 1 |
| 9 | A shape the pass cannot redact | written as-is | **refused** — nothing is written (fail closed) |
| 10 | Nested schema-2 breakdowns | below-floor counts survived in `sites`/`organisations`/`activities` | every row family is dropped on the same rule |

`tests/test_public_reader_floor_browser.py` (from the sibling ticket) asserted the old wording
(`fewer than 10`). It is updated to assert the property this ticket establishes — the row and its
category are *absent* — which is strictly stronger.

## 5. Exact commands

```text
# the audit's own reproduction, unchanged (still reveals the value: it models the old logic)
python3 coordination/evidence/layer3-below-floor-reconstruction/mhpss_public_aggregate_privacy_demo.py
python3 coordination/evidence/layer3-below-floor-reconstruction/test_mhpss_public_aggregate_privacy_demo.py

# failing-first, source at base, tests only  (git checkout 775e142 -- the four app files)
python3 -m unittest tests.test_below_floor_redaction           # FAILED (failures=13)  [RED]
python3 -m unittest tests.test_below_floor_redaction_browser   # FAILED (failures=2)   [RED]

# after the fix
python3 -m unittest tests.test_below_floor_redaction           # OK, 17 tests
python3 -m unittest tests.test_below_floor_redaction_browser   # OK, 2 tests (real Chromium)

# the whole focused surface, together
python3 -m unittest tests.test_publication_privacy_gate tests.test_public_reader_floor_browser \
                   tests.test_hub_publish_ui_browser tests.test_below_floor_redaction \
                   tests.test_below_floor_redaction_browser
Ran 27 tests in 14.486s
OK

# the bilingual gate (both languages, no half-translated string)
python3 apps/public/tools/i18n-check.py                        # exit 0, gate open

# full suite
python3 -m unittest discover -s tests                          # see §5.1
```

### 5.1 Full suite

```text
$ python3 -m unittest discover -s tests
Ran 133 tests in 217.060s
FAILED (failures=1)
```

The single failure is
`tests/test_third_review.py::LocalQAServerSafetyTests::test_browser_helpers_serve_the_application_root_from_any_cwd`.
It is **pre-existing and unrelated**: re-run in a throwaway worktree at base `775e142` with no
local changes, the same test fails the same way (`Ran 6 tests … FAILED (failures=1)`), quoting a
local `404` document on `forms.html` and `access.html`. It is a text-justification/QA-server check
and has nothing to do with the publication shelf; it is left untouched. Every below-floor and
publication-privacy test is green.

## 6. What changed

| File | Change |
|---|---|
| `apps/hub/assets/fb.js` | `redactPublicBody()` — one whole-document pass: a row carrying a below-floor count is dropped; when any row is dropped, every **scalar** count outside a row is withheld; every scalar passes the same floor; the declared floor can never fall below the policy floor. `firstBelowFloorCount()` verifies the result and `publish()` **refuses** (writes nothing) if any below-floor count survived. `FB.REDACTION_FLOOR`, `FB.redactPublicBody` and `FB.belowFloorCount` exposed for the Hub preview and the tests. |
| `apps/public/assets/public-read.js` | `redact()` — the **same algorithm** on the reader side, applied in both `render()` and `preview()` before a single value is drawn; organisation and palika counts now go through `safe()` instead of `num()`. |
| `apps/hub/index.html` | the builder declares the **policy floor**, not `1`, and tags mode through one `DEMONSTRATION_MODE` switch; the publish **preview** now renders the redacted document (what would actually be written), and the panel copy states the suppression rule. |
| `apps/public/assets/i18n-strings.js` | the now-false "small numbers are not suppressed" line corrected in **both** languages. |
| `tests/test_below_floor_redaction.py` | new: the failing-first Node reproduction of every channel (17 tests). |
| `tests/test_below_floor_redaction_browser.py` | new: the real-Chromium check of what the page SHOWS. |
| `tests/test_public_reader_floor_browser.py` | updated to assert the stronger property (the row is dropped, not labelled). |

## 7. Verified vs inferred

**Verified (executed in this worktree):**

- Every channel in §4, by the Node test on the real files, and the rendered-page claims by the
  real-Chromium test. Base red → fix green on the same tests.
- The publisher writes a redacted document and refuses, with zero writes, a document carrying a
  below-floor count it cannot redact.
- `public_stats` is still empty. Read-only, aggregate-only REST check, 2026-09-20:
  `HTTP 200`, body `{}`, **0 documents**. No record body, field value or document ID was printed,
  stored or reproduced. No write of any kind was made to any collection.
- The bilingual gate passes (`i18n-check.py`, exit 0).

**Inferred, not proven:**

- That the deployed server-side Firestore Rules would also enforce this. The Rules are not
  versioned in this repository, so this is a **client-side, fail-closed** control — the same class
  the repo already relies on. It is not a claim about the server.
- That `apps/hub/assets/fb.js` `publish()` is the only writer to `public_stats` within this
  repository. A publisher outside this tree is outside this evidence.

**Residual uncertainty, stated plainly:**

- **The narrower withholding rule.** Rule 2 withholds every scalar count outside a row once any
  row is dropped — more than the minimum. A narrower rule (withhold only the totals a dropped row
  fed) would keep more figures and, by the tests here, still be safe on the fixtures exercised.
  The blunter rule was chosen as the **most protective** option; the narrower one is Adib's call.
- **The threshold where public utility is lost.** Dropping every row below the floor can, with
  sparse real data, empty a district table entirely and withhold the total. What the public page
  should then show is a product decision (see §8).
- **`coordination_full` (schema 2).** Its nested breakdowns are now redacted on the same rule, but
  schema 2 is still not approved to reach `public_stats`; that document is not published by this
  change either way. Whether schema 2 is ever public is not decided here.
- **One fixture artifact.** The synthetic fixture's `basis` was made digit-free so that a figure
  counted off the page is a figure of the *data*, not of the prose. A real basis sentence
  containing digits is not a leak, but the renderer's source note does echo it.
- **One transient test run.** During verification the focused 27-test surface failed **once** with
  no source change; it then passed on three consecutive re-runs (and again at the final head). The
  browser tests drive real Chromium over a local HTTP server, so a launch/timing stall is the
  likely cause. This is stated rather than smoothed over; the failing test names were not captured
  before the re-run. The property is verified by the red→green evidence in §2–§3, which is
  reproducible, not by the single green run.

## 8. Open questions for Adib (no policy was invented)

1. **What the public should see where a row was dropped.** Implemented now: the row and its
   category disappear, and the totals it fed are withheld (blank). That can leave a table showing
   fewer districts than exist, with no explanation. A "some figures withheld" note, or merged
   categories, is a product choice — none was invented.
2. **Is the blunt withholding rule the right one?** Withholding *every* scalar count when any row
   is dropped is the most protective option. A narrower rule would keep more published figures.
   That is a policy decision, not a code one.
3. **Is 10 the Ministry/WHO-approved public floor?** The publisher and reader both enforce the
   floor the public site already used. If the approved floor differs it is a one-line change in
   both files together.
4. **Does the same rule apply to `coordination_full`?** It is redacted on the same algorithm but
   is not approved for `public_stats`; whether it should ever be public is undecided.

## 9. Scope

This ticket closes the **redaction** half only. It did **not** touch referral reconciliation
(`t_5a3012fa`) or the referral safeguarding gate (`t_ed5ad1cf`), did not press Publish, and did not
push, merge, PR or deploy. The publish **guard** (refusing non-production mode, a floor below
policy, and `referral_directory`) is the sibling ticket and is untouched here.
