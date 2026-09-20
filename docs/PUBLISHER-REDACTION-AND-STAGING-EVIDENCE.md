# Publisher-side redaction and staged publishing — evidence

Task `t_33c20f5c`. Status: **DONE — REVIEW ARTIFACT** (with open questions for Adib, §7).
Synthetic fixtures only. No publish was pressed, nothing was written to `public_stats`
or any production collection, and no production ref was modified.

## 1. Base / head

| | |
|---|---|
| Worktree | `/root/mhpss-nepal-work/publisher-redaction` |
| Branch | `fix/publisher-redaction-and-staging` |
| Base | `90eed2efdc210fa44ddb67d8bc16542e31ea171b` (== `architecture/v2-immutable-authority` HEAD) |
| Production refs | public `68bf197`, form `9032bb7`, hub `ff2d4e2` — unchanged; no push / PR / merge / deploy |

The task's assigned worktree (`/root/mhpss-nepal-work/v2-authority-redesign`) held the
staged, **blocked** artifact of the sibling task `t_5a3012fa` (including edits to
`fb.js`). Per the one-task-one-worktree rule, this work ran in a fresh worktree from
the same base; the sibling's staged artifact was left byte-identical (snapshot hashes
in `/tmp/t33c20f5c-foreign/`). No sibling file was edited, reverted or committed.

## 2. What was reproduced first (failing-first)

`tests/test_publisher_redaction.py` drives the **real** publisher and the **real reader**
in a JavaScript engine (Node `vm`): `apps/hub/assets/fb.js` (the only writer to
`public_stats`) and `apps/public/assets/public-read.js` (the renderer the public page
uses). It builds the audit's own minimal case — `contacts = 100`, one visible component
`94`, the complementary cell `6` — and checks every channel named in the finding.

At **base**, before any fix, the test was RED:

```text
python3 -m unittest tests.test_publisher_redaction -v
Ran 14 tests in 1.485s
FAILED (failures=10)
```

and the raw document rendered, in Chromium, as the audit described:

```text
100 service contacts … 100 activity reports … 8 palikas …
service contacts by type of support
small            fewer than 10
large            94
District A       fewer than 10   fewer than 10   1
District B       94              99              20
```

The total `100` and the complement `94` were both on the page while district A showed
"fewer than 10": `100 − 94 = 6` recovered the hidden value.

## 3. What now, after the fix

```text
python3 -m unittest tests.test_publisher_redaction -v
Ran 14 tests in 2.025s
OK
```

The same document renders, in Chromium (`flood-response.html`, real CSS, real reader):

```text
— service contacts … — activity reports … 20 organisations … — palikas …
service contacts by type of support
large            94
District B       94   99   20
```

## 4. Channels closed

Every row below is a **verified** result: the claim is checked by the Node test on the
real files, and the rendered-page claims re-checked in Chromium.

| # | Channel | Before | After |
|---|---|---|---|
| 1 | Complementary-cell arithmetic (total − parts) | `100 − 94 = 6` reconstructable | the below-floor district row is dropped, and any total a dropped row fed is withheld (`contacts`/`reports` → null) |
| 2 | Suppressed row presence | row kept, value "fewer than 10" | row dropped entirely |
| 3 | Category label | the category name is shown | the category name does not appear on the page |
| 4 | Threshold text as a tell | "fewer than 10" rendered | no threshold phrase is rendered for a dropped row |
| 5 | Zero-width bar as a tell | the small family renders a 0-width bar | the small family row is dropped; no 0-width bar is drawn |
| 6 | Bar `max` over raw values | computed over raw values incl. suppressed | the renderer computes `max` over the already-redacted families only |
| 7 | Organisation / palika `num()` bypass | `organisations`/`palikas` rendered with no floor | both go through the same floor; a below-floor count is withheld |
| 8 | Declared floor below policy | a document could declare `suppressed_below: 1` and switch suppression off | a document may not lower the floor: the publisher and the reader both floor at 10 |
| 9 | Demonstration mode reaching the public collection | a demonstration document was written to `public_stats` | a demonstration/review document is staged to `preview_stats`; it cannot reach the collection the public reads |
| 10 | Unapproved document reaching the public collection | any document was written to `public_stats` | only `flood_response` is approved for `public_stats`; anything else is staged |
| 11 | Referral content in the public aggregate | `referral_directory` (organisation × palika) was written to `public_stats` | staged to `preview_stats` — it cannot structurally reach the public aggregate |
| 12 | A raw value already in the collection (read directly) | the reader trusted the document's floor | the reader recomputes the whole-document redaction (defence in depth), floor 10 minimum |

The last row matters because the fix is on the **publisher** (a raw value already in the
collection is exposed to anyone who reads the document directly); the reader change only
stops this site being the place that reveals it.

## 5. Exact commands

```text
# failing-first, at base (source unchanged, test only)
python3 -m unittest tests.test_publisher_redaction -v      # FAILED (failures=10)

# after the fix
python3 -m unittest tests.test_publisher_redaction -v      # OK, 14 tests

# real-browser check of what the page draws (Chromium via Playwright)
python3 /tmp/t33c20f5c-foreign/browser_check.py            # exit 0, all checks true
```

Browser check result (fixed code):

```json
{"page_errors": [], "zero_width_bars": 0,
 "checks": {"no_threshold_phrase": true, "no_suppressed_category": true,
            "no_hidden_value_6": true, "no_zero_width_bar": true,
            "total_and_complement_absent": true, "clean_renders_94": true}}
```

Browser check result (base code, for contrast):

```json
{"checks": {"no_threshold_phrase": false, "total_and_complement_absent": false, ...}}
```

## 6. What was changed

| File | Change |
|---|---|
| `apps/hub/assets/fb.js` | `preparePublicRelease(docId, body)` + a whole-document `redactPublicBody`; `publish()` routes a demonstration/unapproved document to `preview_stats` and redacts an approved one against the policy floor before writing; `readStaged()` added; `public_stats` / `preview_stats` / `POLICY_FLOOR` named. |
| `apps/hub/index.html` | `suppressed_below: 1` removed from both documents (never declared below the policy floor); `DEMONSTRATION_MODE` switch; the panel/banner say plainly what is staged vs published; the preview and the publish result show the prepared body and each document's shelf. |
| `apps/public/assets/public-read.js` | `redact()` — the same decision, whole-document, before anything is drawn, applied in both `render()` and `preview()`. |
| `apps/public/assets/i18n-strings.js` | the now-false "small numbers are not suppressed" claim corrected in both languages; revision bumped. |

## 7. Open questions for Adib (no policy was invented)

1. **What the public should see where a row was dropped.** The most protective option
   was implemented: the row disappears and the totals it fed are withheld. That leaves
   the public page able to show *fewer* districts than exist, and the total blank, with
   no explanation. A "some figures withheld" note, or merged categories, is a product
   choice for Adib/the Ministry — none was invented.
2. **Whether `referral_directory` should be public at all.** It is now **staged** to
   `preview_stats`, per our own rule that referral content must not structurally reach
   the public aggregate. If it is meant to be public, that is a decision, not a bug.
3. **`preview_stats` must exist server-side.** The client now writes staged documents
   there. Until the Firestore Rules create/allow that collection, a staged write will be
   refused by the server — the correct fail-closed default, but it must be confirmed
   before the review flow is relied on.
4. **`coordination_full` is staged**, not published, until someone decides it should be.

## 8. Verified vs inferred, and residual uncertainty

- **Verified:** every channel in §4, by the Node test on the real files, and the rendered
  page in Chromium. Base red → fixed green, on the same test.
- **Inferred (not verified):** the live Firestore Rules are not in this tree, so whether
  the server permits `preview_stats` and refuses a floor-of-1 write is **unverified**.
  The client-side control is real; server enforcement is assumed, and stated as such in
  the code comments, exactly as the sibling tasks do.
- **Residual uncertainty:** the exact set of totals to withhold when a row is dropped is
  a conservative choice (withhold the breakdown totals); a more granular rule could keep
  more figures without reopening the arithmetic channel. That is a design refinement for
  Adib, not a correctness gap in the channels tested.
