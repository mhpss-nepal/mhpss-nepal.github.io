# Below-floor redaction, computed once per document

Task `t_f3b83790` — *Fix: compute below-floor redaction once per document, not per number*.
Tenant `mhpss-nepal` · branch `architecture/v2-immutable-authority` (review artifact, **not deployed**).

| Field | Value |
|---|---|
| Worktree | `/root/mhpss-nepal-work/v2-authority-redesign` — sole task on it (checked before starting, and again before round 2) |
| Base (parent of round-2 work) | round-1 head `86a4054ebfb7c3bae9c9ff0f1f3911b7f51f7d31`; the work began at `775e142c2a37324bb74af9d58cf880f626174367` |
| Test-only commits (round 1, red) | `04af6d7` (core channels), `b96303c` (browser + fail-closed + clean + idempotency + nested) |
| Fix commit (round 1, green) | `a3b3a218171886f4fef17d4e1a6c0f6e46dc98bb` |
| Review | rounds 1 and 2 **changes requested** — see §§10 and 13. The candidate was corrected after each adversarial reproduction. |
| Test-only commits (round 2, red) | `904b4fd`, `a1b76ca`, `b1eed00` |
| Fix commit (round 2, green) | `1627307` — withhold enclosing row totals after a nested drop; verify against the effective floor |
| Test-only commit (round 3, red) | `f036605` — leading `null` and leading primitive mixed-row fixtures on publisher, reader, and real Chromium |
| Fix commit (round 3, green) | `829dc36` — reject malformed mixed aggregate row families before publisher redaction or reader rendering |
| Test-only commit (round 4, red) | `52526de` — plain-object nested-scalar complementary fixture |
| Fix commit (round 4, green) | `34036f9` — propagate nested scalar suppression to covering totals and complements |
| Review round 4 | **changes requested** — the structural-key classifier (§14) |
| Test-only commit (round 5, red) | `74e9b566` — below-floor scalar **and** subtree under **each** of the six reserved names below the root, publisher + reader, driven by an oracle independent of `NOT_A_COUNT` |
| Fix commit (round 5, green) | `ecc15af` — scope the structural-key exemption to the document **root** (§15) |
| Head | the commit carrying this file; its SHA-1 and SHA-256 are recorded in the kanban completion metadata, so this document does not embed its own id |
| Production refs | public `68bf197`, form `9032bb7`, hub `ff2d4e2` — **no push / PR / merge / deploy by this task** |
| ⚠ Public `main` moved during the work | to `c32b6e8`, **by another actor, not this task** — see §12 |
| Worktree after the fix | clean |
| Status | **DONE - REVIEW ARTIFACT** with open questions for Adib (§8) and one named residual boundary (§15.4) |

Synthetic fixtures only. No Publish was pressed, nothing was written to `public_stats` or
any other collection, and the live check was read-only and aggregate-only.

> **Round-2 note, read this before §1.** Round 1 claimed the class was closed. A review
> reproduced two survivors at round-1 head `86a4054` and was right. §10 records both
> reproductions, the fix, and — plainly — what round 1 got wrong. The claim in this document
> is now scoped to what its tests actually exercise, and §11 states the residual limit.

> **Round-3 note.** A second adversarial review found that `isRowFamily` looked only at array
> member 0. A leading `null` or primitive made later aggregate rows bypass row-family handling.
> §13 records the failing-first reproduction and the fail-closed correction.

> **Rounds 4–5 note.** A third review moved the same arithmetic into a plain-object scalar (§14).
> A fourth review then found the **classifier** itself: the six structural key names were exempted
> by *name at every depth*, so a below-floor count or subtree under one of them below the root was
> invisible to both the suppression pass and the verifier. §15 records the root-scoping fix, which
> is the class-level correction the parent directed (the same criterion had returned unchanged
> through four shapes). The exemption is now a fact about the document **root**, where it is
> genuinely bookkeeping, not a property of the name everywhere.

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
Ran 23 tests in 2.529s

OK

$ python3 -m unittest tests.test_below_floor_redaction_browser -v
Ran 4 tests in 8.747s

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

The *nested* case (§10) is written as — the enclosing row's own total is `null`, while the
surviving nested sibling keeps its own above-floor figures:

```json
{ "districts": [ { "code": "A", "contacts": null,
                   "breakdown": [ {"family": "large", "contacts": 94} ] } ] }
```

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
| 11 | **Nested drop leaves the enclosing total** *(round 2 — round 1 missed it)* | a surviving nested complement was subtracted from its enclosing row's own published total: `100 − 94 = 6` | every ancestor of a dropped row that could carry a covering total is **tainted** and its own scalar counts withheld, at any depth and through any container |
| 12 | **Fail-closed check used the constant floor** *(round 2)* | a document declaring floor 20 had its value 15 written, because verification compared against 10 | publisher **and** reader verify against the document's **effective** floor; the reader also refuses (draws nothing for) a shape it cannot fully redact |

Rows 11 and 12 are the review's reproductions and were **not** covered by round 1 — see §10.

`tests/test_public_reader_floor_browser.py` (from the sibling ticket) asserted the old wording
(`fewer than 10`). It is updated to assert the property this ticket establishes — the row and its
category are *absent* — which is strictly stronger.

## 5. Exact commands

```text
# the audit's own reproduction, unchanged (still reveals the value: it models the old logic)
python3 coordination/evidence/layer3-below-floor-reconstruction/mhpss_public_aggregate_privacy_demo.py
python3 coordination/evidence/layer3-below-floor-reconstruction/test_mhpss_public_aggregate_privacy_demo.py

# failing-first, round 2, at the TEST-COMPLETE commit with the fix not yet applied
# (scratch worktree at b1eed00 — the true forward direction, not a checkout of app files)
git worktree add --detach /tmp/redpoint-b1eed00 b1eed00
cd /tmp/redpoint-b1eed00
python3 -m unittest tests.test_below_floor_redaction           # FAILED (failures=12)  [RED]
python3 -m unittest tests.test_below_floor_redaction_browser   # FAILED (failures=2)   [RED]
# (fsck-style check that the fix is genuinely absent here: `grep -c tainted` = 0 in both app files)
cd -; git worktree remove /tmp/redpoint-b1eed00

# after the round-2 fix
python3 -m unittest tests.test_below_floor_redaction           # OK, 23 tests
python3 -m unittest tests.test_below_floor_redaction_browser   # OK, 4 tests (real Chromium)

# the whole focused surface, together
python3 -m unittest tests.test_publication_privacy_gate tests.test_public_reader_floor_browser \
                   tests.test_hub_publish_ui_browser tests.test_below_floor_redaction \
                   tests.test_below_floor_redaction_browser
Ran 35 tests in 29.0s
OK

# the bilingual gate (both languages, no half-translated string)
python3 apps/public/tools/i18n-check.py                        # exit 0, gate open

# full suite
python3 -m unittest discover -s tests                          # see §5.1
```

### 5.1 Full suite

```text
$ python3 -m unittest discover -s tests
Ran 141 tests in 234.824s
FAILED (failures=1)
```

The single failing test that run is
`tests/test_third_review.py::LocalQAServerSafetyTests::test_browser_helpers_serve_the_application_root_from_any_cwd`.
It is **pre-existing and unrelated**: re-run in a throwaway worktree at the round-1 head `86a4054`
with no local changes, it fails the same way (`Ran 1 test … FAILED (failures=1, errors=1)`),
quoting a local `404` document on `forms.html` and `access.html`, and timing out one helper. It is
a text-justification/QA-server check and has nothing to do with the publication shelf; it is left
untouched.

### 5.1.1 A second, intermittent failure — diagnosed, pre-existing, NOT fixed here

The failed run above also carries a flake that only appears roughly **5–8 % of the time**:

```text
FAIL: test_what_the_page_would_publish_is_refused_by_the_real_sink
      (tests.test_hub_publish_ui_browser.HubPublishUiBrowserTests)
AssertionError: [] is not true : the page sent nothing to publish
```

It is worth naming precisely, because a test that fails one run in twenty is exactly the thing
that gets waved away as "a launch stall". It is not a launch stall.

**Mechanism (verified, not inferred).** The test drives the *real* Hub page, then:

1. `apps/hub/index.html:1730` has `pubAuthPaint()` set `$("pubGo").disabled = true;` — the publish
   button starts disabled;
2. the test replaces `window.FB.publish`, then sets `document.getElementById('pubGo').disabled = false`
   (`tests/test_hub_publish_ui_browser.py:100`) and clicks;
3. but `pubAuthPaint()` is *also* invoked asynchronously by
   `window.FB.onStatus(function () { … pubAuthPaint(); })` (`index.html:1757`) — **and by the first
   click of the Publish tab** (`index.html:1759`). When a late repaint wins the race, line 1754
   runs `$("pubGo").disabled = !ok;` with no signed-in user, so `ok` is false and the button is
   **re-disabled between the test's write and its click**; the click is then swallowed by a
   disabled button, and nothing is captured.

Measured directly with a probe that enables the button and samples `.disabled` every 50 ms:
`[False, True, True, True, …]` — enabled, then re-disabled within ~50 ms.

**Verified as pre-existing, and not introduced by this ticket:**

```text
$ git log --oneline 86a4054..HEAD -- tests/test_hub_publish_ui_browser.py
(no output — round 2 never touched it)

$ git show <ref>:tests/test_hub_publish_ui_browser.py   # blob ids identical at all three refs
775e142  4e67980a1c0d8f2fc10a87cbc9ba55a7641555e8
86a4054  4e67980a1c0d8f2fc10a87cbc9ba55a7641555e8
HEAD     4e67980a1c0d8f2fc10a87cbc9ba55a7641555e8

$ # app source checked out at the pre-round-2 base 775e142, 25 runs:
failures at 775e142 source: 2 / 25          # ≈ 8 %
$ # round-2 head, 40 runs:
failures: 2 / 40                            # ≈ 5 %
```

**Why it is not fixed here.** It is a **test-harness race, not a product defect**: the page's
behaviour (a signed-out user cannot publish) is correct and is what the sibling guard relies on.
Fixing it means changing `tests/test_hub_publish_ui_browser.py` — a sibling ticket's test — and
this ticket's constraint is that a channel is not closed without its own failing-first test, which
the same rule applies to. Recorded here so the next reader does not rediscover it as a mystery.

**What it means for this ticket's evidence.** The focused 35-test surface was run **seven
consecutive times** and passed all seven; one earlier run of it failed on exactly this pre-existing
flake. The below-floor suites (§2–§4) do not touch `test_hub_publish_ui_browser.py` and ran clean
throughout.

### 5.2 Two pieces of this ticket's own work that are stated, not smoothed over

`tests/test_third_review.py` is not the only awkwardness worth naming:

- The round-2 browser reproduction was **rewritten** after a first attempt passed at base. The
  first version asserted that a nested leaked value was not *drawn* by the public page — true at
  base for the wrong reason (the schema-1 renderer never draws a `breakdown` field at all), so it
  proved nothing. It now drives the page's own `window.PUBLIC_STATS.redact()` layer, which does
  fail at base. A test that passes for a reason unrelated to the defect is not evidence.
- Round 1's `test_nested_schema_two_counts_are_redacted_too` **passed while the defect was live**:
  it asserted only that no below-floor *number* survived, and the surviving complement (94) is
  above the floor. It is the reason §4 row 10 overstated what round 1 had closed. The assertion
  was true and the conclusion drawn from it was wrong.

## 6. What changed

| File | Change |
|---|---|
| `apps/hub/assets/fb.js` | `redactPublicBody()` — one whole-document pass: a row carrying a below-floor count is dropped; when any row is dropped, every **scalar** count outside a row is withheld; an **enclosing** object whose own subtree lost a row is tainted and its scalar counts withheld too (round 2); every scalar passes the same floor; the declared floor can never fall below the policy floor. `firstBelowFloorCount()` verifies the result **against the document's effective floor** (round 2) and `publish()` **refuses** (writes nothing) if any below-floor count survived. `FB.REDACTION_FLOOR`, `FB.redactPublicBody` and `FB.belowFloorCount` exposed for the Hub preview and the tests. |
| `apps/public/assets/public-read.js` | `redact()` — the **same algorithm** on the reader side, applied in both `render()` and `preview()` before a single value is drawn; organisation and palika counts now go through `safe()` instead of `num()`; the ancestor-taint rule mirrored (round 2); and a document it cannot fully redact is **refused** — `redact()` throws, and both call sites draw none of the document (round 2). |
| `apps/hub/index.html` | the builder declares the **policy floor**, not `1`, and tags mode through one `DEMONSTRATION_MODE` switch; the publish **preview** now renders the redacted document (what would actually be written), and the panel copy states the suppression rule. |
| `apps/public/assets/i18n-strings.js` | the now-false "small numbers are not suppressed" line corrected in **both** languages. |
| `tests/test_below_floor_redaction.py` | new: the failing-first Node reproduction of every channel (17 tests in round 1; **23** after the round-2 regressions for the ancestor class and the effective floor). |
| `tests/test_below_floor_redaction_browser.py` | new: the real-Chromium check of what the page SHOWS (2 tests in round 1; **4** after round 2). |
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
- **The ancestor rule is structural, not analytic.** Round 2 withholds the scalar counts of
  *every* enclosing object whose subtree lost a row. It is deliberately blunt in the same way: it
  does not know which ancestor total actually sum-covered the dropped member, so it withholds them
  all. That is the protective choice, and it can empty more of a nested document than the minimum.
- **Sum relationships across sibling branches are still not analysed.** The fix removes a
  *dropped* row's covering totals. It does not attempt the general complementary-cell problem
  where two published cells in different branches happen to overlap the same population. See §11.
- **The threshold where public utility is lost.** Dropping every row below the floor can, with
  sparse real data, empty a district table entirely and withhold the total. What the public page
  should then show is a product decision (see §8).
- **`coordination_full` (schema 2).** Its nested breakdowns are now redacted on the same rule, but
  schema 2 is still not approved to reach `public_stats`; that document is not published by this
  change either way. Whether schema 2 is ever public is not decided here.
- **One fixture artifact.** The synthetic fixture's `basis` was made digit-free so that a figure
  counted off the page is a figure of the *data*, not of the prose. A real basis sentence
  containing digits is not a leak, but the renderer's source note does echo it.
- **The reader refuses by drawing nothing.** A schema-1 document the reader cannot fully redact
  renders the "cannot be read" state with no figures. That is fail-closed, but it is also a new
  blank-page behaviour for a malformed document — noted here rather than left to be discovered.
- **One transient test run — now diagnosed.** During round-1 verification the focused surface failed
  **once** with no source change, and it passed on re-runs; round 1 recorded it as "likely a
  launch/timing stall" and could not name it. Round 2 found and diagnosed it: it is a real race in
  a **sibling ticket's** test harness (`test_hub_publish_ui_browser.py` re-enables a button that the
  page re-disables), reproduces at ~5–8 % at three different refs including the pre-round-2 base,
  and is **not** a product defect. Full mechanism and measurements in §5.1.1. Round 1's guess was
  wrong, and the honest version is now written down.
- **One process consequence, stated for the record.** A stale `python3 -m http.server` (started
  ~4h48m earlier, serving `apps/public`) was still bound to port 9071 from a *previous* run of
  this task, and `tests/test_hub_publish_ui_browser.py` `_serve()` binds a fresh free port each
  time, so concurrent browser suites can still collide with a leftover. It was left running
  because it is this task's own residue and killing it would have changed state mid-verification;
  it bound loopback and served read-only. A later attempt should check for it.

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
5. **Should a document the reader cannot fully redact show a "cannot be read" state, or nothing?**
   Implemented now: the page draws no figures and says the summary cannot be read. An alternative
   is to render a plain "withheld" line. Cosmetic, but it is the reader's failure mode.

## 9. Scope

This ticket closes the **redaction** half only. It did **not** touch referral reconciliation
(`t_5a3012fa`) or the referral safeguarding gate (`t_ed5ad1cf`), did not press Publish, and did not
push, merge, PR or deploy. The publish **guard** (refusing non-production mode, a floor below
policy, and `referral_directory`) is the sibling ticket and is untouched here.

---

## 10. Round 2 — the two review reproductions, and what round 1 got wrong

The round-1 review (`changes_requested` at `86a4054`) reproduced two survivors. Both were real;
both are now closed failing-first.

### 10.1 Reproduction 1 — a nested drop left the enclosing row total published

Round-1 `dropRows` recursed into a nested array with the marker `inRow=false`, and returned
nothing about whether a row had been dropped inside a subtree. So for

```json
{ "contacts": 100,
  "districts": [ { "code": "A", "contacts": 100,
                   "breakdown": [ {"family": "small", "contacts": 6},
                                  {"family": "large", "contacts": 94} ] } ] }
```

the nested `small` row was dropped and the top-level `100` was withheld — but the district row's
**own** `contacts: 100` survived alongside the surviving nested `94`. `100 − 94 = 6`. Published
value reconstructed, exactly the class this ticket exists to close.

**Why round 1 missed it.** Its narrowest remaining assumption was "a survivor row's own figures
are all safe because they are at or above the floor." That is true of each figure *individually*
and false of the *set*: a survivor's own total can sum-cover a dropped member one level down.
Round 1 fixed the per-number rule and left a per-level version of the same mistake.

**The fix (commit `1627307`).** Pass 1 now returns whether any row was dropped in the subtree it
walked. When a row loses something inside it, that row is pushed onto `state.tainted`; pass 2
withholds the scalar counts of any tainted object. A *surviving nested row* is a fresh region and
keeps its own figures, because it cannot cover the dropped member — only its ancestors can.

### 10.2 Reproduction 2 — fail-closed verification used the constant floor

`publish()` verified the redacted document with `firstBelowFloorCount(out, PUBLIC_SUPPRESSION_FLOOR, "$")`
— always `10`, even when the document declared `suppressed_below: 20`. A matrix value of `15` was
therefore below the document's *effective* floor, survived the pass (the pass does not know how to
redact a numeric array), and was written. The reviewer's exact output showed `declared_floor: 20`
beside unredacted matrix values, with `belowFloorCount(…, REDACTION_FLOOR)` reporting no leak.

**The fix.** `publish()` and the reader's `redact()` both verify against
`policyFloor(out.suppressed_below)` — the document's **effective** floor — so a value between the
policy default and the declared floor is caught, not waved through.

### 10.3 The class, not the shape

Closing the reviewer's exact fixture is necessary and not sufficient. The same arithmetic can be
moved one structure away, so the round-2 tests also cover:

| Fixture | Structure | Withheld after the fix |
|---|---|---|
| three levels of nesting | `districts[].zones[].hamlets[]` | `districts[0].contacts` **and** `districts[0].zones[0].contacts` |
| a non-row container | a plain object (`grid`) holding a `total` beside a `cells` list | the row's `contacts` **and** `grid.total` |
| an object inside a row | a `meta` object holding a `total` beside its own `rows` list | the row's `contacts` **and** `meta.total` |

and each runs on **both** the publisher and the reader.

### 10.4 Round 1's claims that did not hold

| Round-1 claim | What actually happened |
|---|---|
| §4 row 10, "nested schema-2 breakdowns — every row family is dropped on the same rule" | dropping the family was true; leaving the *enclosing* total was not covered. The claim was broader than the test behind it. |
| "A channel that is not covered by a failing-first test is not closed." | correct as a rule — and round 1 violated it for the ancestor channel while claiming it closed. |
| The full suite had one pre-existing failure | true, but the run *also* carried a second, intermittent failure round 1 never mentioned because it saw a green re-run. It is real, diagnosed in §5.1.1, and pre-existing. |
| The transient focused-run failure was "a launch/timing stall" | wrong. It is a reproducible button re-enable race in a sibling ticket's harness. |
| One reviewed repair fixed everything | false for the class; true only for the reviewer's exact fixture, and only after round 2. |

Round 1 also had a **passing test that proved nothing** — see §5.2.

## 11. What is still not closed (the boundary of this fix)

Stated plainly, so this is not read as "the class is closed for all aggregate documents":

- **Overlapping breakdowns that were never dropped.** The pass removes a dropped row and the
  totals of its ancestors. It does **not** analyse whether two *surviving* published cells in
  different branches cover the same population and reveal a third. Detecting that needs a real
  cross-field sum model of the document, which schema-1/schema-2 fixtures do not carry and which
  this ticket does not invent.
- **Its fail-closed refusal only catches what it can recognise.** An unrecognised shape carrying a
  below-floor count is refused only when the count is *detectable as a number*. A count smuggled
  in as a string, or a derived ratio, is outside what `firstBelowFloorCount` walks.
- **Rounding, ratio inversion, and row-count/ordering channels** are addressed by the reader's
  geometry changes (§4 rows 5–6) but not by a general coherent-rounding rule.
- **Server-side enforcement is unverified** — the deployed Firestore Rules are not versioned in
  this repository, so all of this is a **client-side, fail-closed** control.

A future publisher change that adds a new item family adds a new surface; the checklist in
`references/aggregate-privacy-and-small-cells.md` is the right instrument for it, not this doc.

## 12. The production public ref moved during this work — not by this task

The task's constraint was that production refs stay unchanged. At the start of round 2 they were
public `68bf197`, form `9032bb7`, hub `ff2d4e2`. Re-checking at the end:

```text
$ git -C mhpss-nepal-audit-20260918/mhpss-nepal.github.io rev-parse --short HEAD
c32b6e8

$ git -C mhpss-nepal-audit-20260918/hub  rev-parse --short HEAD     # ff2d4e2
$ git -C mhpss-nepal-audit-20260918/form rev-parse --short HEAD     # 9032bb7
```

`mhpss-nepal.github.io` `main` is now `c32b6e8` ("Contact emblems, an audit/assessment group, and
a real publisher on every card", authored 2026-09-20 12:57Z), where this session started at
`68bf197`.

**This task did not move it.** Evidence:

- Its reflog holds exactly two entries — the original clone, then
  `c32b6e8 main@{0}: merge origin/main: Fast-forward`, i.e. someone fetched and fast-forwarded the
  production checkout, which this task has no workflow for (it never ran `git fetch` or `git merge`
  in that repository, and never pushed anything from anywhere).
- `c32b6e8` is **not** an ancestor of this task's branch — this task never pulled it.
- The same subject is the HEAD of the *other* worktree
  `/root/mhpss-nepal-work/public-layer3` (`e191d27`, same message), i.e. the change is the public
  layer-3 line of work reaching production over its own release path, concurrently with this
  session.

**Does it affect this finding?** No, and that is checked, not assumed:

- `git diff --quiet 68bf197 c32b6e8` shows **zero** change to `assets/public-read.js`,
  `hub/assets/fb.js`, and `hub/index.html` — the three files this ticket touches. The 24 changed
  files are site content/CSS/assets.
- The deployed reader is still the vulnerable one, byte for byte, at **both** refs:
  `sha256( live assets/public-read.js )` =
  `c176d35779f9406c970023e123197e2b3e41c68d908363dfbcb5d211e3820f55`, identical to `68bf197` and
  to `c32b6e8`.

**What is still true:** the fix in this ticket is **not deployed and not reachable from
`main`** — `c32b6e8` does not contain it — so the below-floor reconstruction channel remains live
on the public site, exactly as the audit found. Nothing here changes that; it is also the reminder
that releasing this fix is a separate, deliberate step, as the standing rule requires.

## 13. Round 3: malformed mixed row families fail closed

### 13.1 Reproduction (failing first)

The second review supplied two malformed-but-valid-JSON variants:

- `families: [null, {small: 6}, {large: 94}]`
- `families: ["unexpected", {small: 6}, {large: 94}]`

At head `4c23123`, `isRowFamily` classified an array only from member 0. Both variants therefore
published a document retaining total 100, complement 94, and the `small` category; the reader
accepted the same shape. Real Chromium threw on the leading `null` instead of failing closed.

The regression tests were committed before the runtime fix in `f036605`. Exact focused command:

```text
$ python3 -m unittest \
  tests.test_below_floor_redaction.BelowFloorRedactionTests.test_publisher_refuses_mixed_row_families_without_writing \
  tests.test_below_floor_redaction.BelowFloorRedactionTests.test_reader_refuses_mixed_row_families \
  tests.test_below_floor_redaction_browser.BelowFloorRenderBrowserTests.test_the_real_page_refuses_mixed_row_families_without_throwing -v
Ran 3 tests in 2.678s
FAILED (failures=5, errors=1)
```

The failures were the required signals: two publisher writes, two reader acceptances, one browser
throw, and one browser acceptance.

### 13.2 Correction and verified policy

Commit `829dc36` validates every member before redaction. If an array contains both plain-object
aggregate rows and any non-row member, the publisher refuses it with **zero writes**, and the
reader refuses it and renders **nothing**. The code does not silently filter the foreign member:
that would invent a data-repair policy and could alter the meaning of a published aggregate.
Homogeneous object-row arrays and homogeneous non-object arrays retain their existing handling.

The same focused command at `829dc36`:

```text
Ran 3 tests in 2.657s
OK
```

Publisher + reader + real-browser focused suites:

```text
$ python3 -m unittest tests.test_below_floor_redaction tests.test_below_floor_redaction_browser -v
Ran 30 tests in 13.732s
OK
```

This closes the round-2 review's category-presence, complementary-arithmetic, and availability
reproductions for leading `null` and leading primitive members. It does not change the broader
residual boundaries in §11.

## 14. Round 4: nested scalar suppression propagates to covering totals and complements

### 14.1 Reproduction (failing first)

The third review moved the same complementary-cell arithmetic out of a nested row family and into
a plain object:

```text
contacts: 100
districts[0].contacts: 100
districts[0].detail: { small: 6, large: 94 }
```

At `53a6555`, the publisher and reader withheld `detail.small` but retained the district total and
`detail.large`, so the raw document still yielded the withheld value by subtraction. Tests were
committed before the runtime change in `52526de`.

Exact red command:

```text
$ python3 -m unittest \
  tests.test_below_floor_redaction.BelowFloorRedactionTests.test_nested_scalar_suppression_taints_every_covering_published_total \
  tests.test_below_floor_redaction.BelowFloorRedactionTests.test_reader_propagates_nested_scalar_suppression_to_covering_totals -v
Ran 2 tests in 0.196s
FAILED (failures=2)
```

Both failures were the intended signal: the district total was still `100` in the publisher output
and in the reader's redacted document.

### 14.2 Correction

Commit `34036f9` adds a separate scalar-suppression propagation pass to publisher and reader. A
below-floor scalar now marks:

- its direct object, whose numeric siblings are withheld so no complement remains;
- every enclosing object, whose own numeric totals are withheld because they may cover that scalar;
- the document root, whose covering totals are likewise withheld.

This is intentionally conservative because the schema does not encode lineage proving that a
particular sibling or ancestor is independent. It does not alter the scalar-only top-level case:
that one below-floor field is still withheld while clean row families survive.

The exact two-test command after the fix:

```text
Ran 2 tests in 0.148s
OK
```

The full focused publisher + reader + real-Chromium surface after the fix:

```text
$ python3 -m unittest \
  tests.test_below_floor_redaction \
  tests.test_below_floor_redaction_browser \
  tests.test_publication_privacy_gate \
  tests.test_public_reader_floor_browser \
  tests.test_hub_publish_ui_browser -v
Ran 40 tests in 23.722s
OK
```

No extra browser test was added for this fixture because `detail` is not a field the schema-1 flood
renderer displays. The reader's real redaction function is exercised through the existing Node VM
harness; the real Chromium suite was rerun to ensure the page surface and existing rendered
channels remained green.

### 14.3 What this round closes and does not claim

Verified closed in this round: a scalar actively withheld by this redaction pass cannot retain its
same-object complement or any enclosing numeric total at the publisher or reader. The broader
residual boundary in §11 still applies to overlapping values that are all above the floor and were
never suppressed by this pass, string-encoded counts, derived ratios, and unverified server-side
rules.

## 15. Round 5: the structural-key exemption is scoped to the document root (supersedes §14's classifier entry)

### 15.1 The defect: a fact about the root generalised to a property of the name

`NOT_A_COUNT` (`apps/hub/assets/fb.js`) and the identical `NOT_A_COUNT`
(`apps/public/assets/public-read.js`) list six names — `schema`, `schema_version`,
`suppressed_below`, `period_from`, `period_to`, `codes_version` — that are bookkeeping, not counts
about people. The code consulted that list **by name at every depth**:

```js
if (NOT_A_COUNT[k]) continue;   // firstBelowFloorCount / firstBelowFloor
```

That is correct at `$`, where those names really are metadata. It is wrong anywhere below `$`:
the same name is then an ordinary field, but the suppression pass *skips it entirely* and the
fail-closed verifier *does not look at it*, so a below-floor count (or a whole below-floor subtree)
beneath one of those names survives redaction beside a covering total and its complement. This is
the same complementary-cell criterion the audit opened, reached through the classifier
(release-safety §2b: when rounds keep exposing one class in a new shape, attack the classifier).

### 15.2 Reproduction (failing first)

Two synthetic fixtures per name, both retaining the audit's `100 − 94 = 6` arithmetic:

```text
contacts: 100
districts[0].contacts: 100
districts[0].detail: { <reserved name>: 6,   large: 94 }     # scalar under a reserved name
districts[0].detail: { <reserved name>: { small: 6, large: 94 } }   # subtree under a reserved name
```

The oracle that reads the result back is **independent of the code under test**: it walks the
document itself and exempts the six names **only at the root**
(`below_floor_numbers_root_scoped` in `tests/test_below_floor_redaction.py`). Crucially it does not
call `below_floor_numbers` / `_STRUCTURAL_KEYS`, which shared the same at-every-depth blind spot —
that shared blind spot is exactly why earlier suite runs passed while the leak was present.

Failing-first, at test-only commit `74e9b566` with the runtime fix absent (throwaway worktree
`/tmp/bfr-red`, so the shared worktree was never left in a red state):

```text
$ python3 -m unittest tests.test_below_floor_redaction tests.test_below_floor_redaction_browser
Ran 38 tests in 17.115s
FAILED (failures=25)
```

The focused classifier-only command at the same commit (5 tests, 24 subtest failures):

```text
$ python3 -m unittest \
  tests.test_below_floor_redaction.BelowFloorRedactionTests.test_publisher_closes_root_only_key_classifier_for_nested_scalars \
  tests.test_below_floor_redaction.BelowFloorRedactionTests.test_publisher_closes_root_only_key_classifier_for_nested_subtrees \
  tests.test_below_floor_redaction.BelowFloorRedactionTests.test_reader_closes_root_only_key_classifier_for_nested_scalars \
  tests.test_below_floor_redaction.BelowFloorRedactionTests.test_reader_closes_root_only_key_classifier_for_nested_subtrees \
  tests.test_below_floor_redaction.BelowFloorRedactionTests.test_legitimate_root_bookkeeping_remains_exempt
Ran 5 tests in 2.337s
FAILED (failures=24)
```

Sample failure, showing the raw value reaching the shelf:

```text
AssertionError: Lists differ: [('$.districts[0].detail.suppressed_below.small', 6)] != []
```

Real Chromium, the page's own `redact()` at the same commit, failed the same way
(`test_the_real_page_does_not_honour_a_nested_structural_name`):

```text
AssertionError: 6 is not None : the page kept a below-floor value under a nested reserved name
```

### 15.3 Correction

Commit `ecc15af` (green) replaces the name-only check with a path-aware one in **both** files:

```js
/* a structural name is exempt only where it actually means structure: the root */
function isBookkeepingKey(key, depth) {
  return (depth || 0) === 0 && !!NOT_A_COUNT[key];
}
```

`depth` is threaded through every walker that consults the exemption — `rowHasBelowFloor`,
`markScalarTaints`, `nullAggregates`, `firstBelowFloorCount` in `fb.js`; `rowHasBelowFloor`,
`dropRows`, `markScalarTaints`, `nullAggregates`, `firstBelowFloor` in `public-read.js` — started
at `0` from `redactPublicBody` / `redact`. Below `$` a reserved name is now an ordinary count: it
is suppressed, it can taint an ancestor, and the verifier will see and refuse a survivor. This is
the class-level fix the parent directed (root-scoping in both files), applied once, not another
shape patch.

Focused classifier command at `ecc15af`:

```text
Ran 5 tests in 1.729s
OK
```

### 15.4 What closed, what is a named boundary, and what stays open

**Closed in this round (failing-first, publisher + reader, plus real Chromium on the page):**

| Channel | Test |
|---|---|
| below-floor **scalar** under each of the six reserved names below the root | `test_publisher_closes_root_only_key_classifier_for_nested_scalars`, `test_reader_closes_root_only_key_classifier_for_nested_scalars` |
| below-floor **subtree** under each of the six reserved names below the root | `test_publisher_closes_root_only_key_classifier_for_nested_subtrees`, `test_reader_closes_root_only_key_classifier_for_nested_subtrees` |
| real page's own `redact()` on a nested reserved-name subtree | `test_below_floor_redaction_browser...test_the_real_page_does_not_honour_a_nested_structural_name` |
| root-level bookkeeping (`schema`, `schema_version`, `suppressed_below`, `period_from`, `period_to`, `codes_version`) still publishes | `test_legitimate_root_bookkeeping_remains_exempt` |

**Named residual boundary — this is a latent classifier hole, not a live self-inflicted leak.**
This repository's own publisher (`apps/hub/index.html:1629-1635,1697`) emits those six names only
at the document **root**, so the Hub does not produce a document that reaches this hole today. The
hole is reachable by a **foreign, older, or hand-written document** — precisely the case the
reader's defence-in-depth exists for, and precisely the case the fail-closed verifier claimed to
cover but did not. Stated plainly so this is not read as a currently-live leak: **no document this
publisher builds exploits it; the fix removes a latent tunnel a differently-written document could
use.** No such document was observed anywhere; this was found by the reviewer against synthetic
input, and the fixture is synthetic.

**Still open, unchanged from §11:** overlapping above-floor survivors this pass was never asked to
suppress; string-encoded counts and derived ratios; and unverified server-side Firestore Rules.
No new class is opened here, and no shape-by-shape hardening beyond the six reserved names was
added.

### 15.5 Round-5 verification commands (exact)

```text
$ python3 -m unittest \
  tests.test_below_floor_redaction \
  tests.test_below_floor_redaction_browser \
  tests.test_publication_privacy_gate \
  tests.test_public_reader_floor_browser \
  tests.test_hub_publish_ui_browser
Ran 46 tests in 26.320s
OK
```

(publisher + reader + real Chromium focus alone: `Ran 38 tests in 17.113s` — `OK`; re-run three
times, `OK` each time. The wider focused surface above was `OK` on three consecutive runs.)

Full suite:

```text
$ python3 -m unittest discover -s tests
Ran 152 tests in 227.922s
FAILED (failures=1)
```

The single failure is **pre-existing and unrelated**: `test_third_review`
`test_browser_helpers_serve_the_application_root_from_any_cwd` (`forms.html`/`access.html` render
a `404 - Nothing matches` block that is not justified). Re-confirmed at the true base
`775e142` in a clean throwaway worktree (`/tmp/bfr-base`):

```text
$ python3 -m unittest discover -s tests -p "test_third_review.py"
Ran 6 tests in 182.251s
FAILED (failures=1)
FAIL: test_browser_helpers_serve_the_application_root_from_any_cwd
      (test_third_review.LocalQAServerSafetyTests...) (relative='apps/hub/tools/justify-sweep.py')
```

It is not fixed here (out of scope) and was not touched by this change.

### 15.6 Round 5 does not weaken any earlier gate

Every shape found in rounds 1–4 was re-run at `ecc15af` and still fails closed: nested row
complement, the declared-floor-vs-verifier case, mixed row families (leading `null` and leading
primitive), and the plain-object nested scalar. All are in the `Ran 46 … OK` run above. Live
aggregate-only check, read-only, no body printed:

```text
public_stats → HTTP 200, documents_returned 0
```

`git diff --check ce22e18..HEAD` exits `0` (no whitespace errors); the worktree is clean.
