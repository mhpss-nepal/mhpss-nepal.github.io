# Guard: no document may reach the public collection with suppression disabled

Task: `t_4d8a95a0` — *Guard: no document may reach the public collection with suppression disabled*
Tenant: `mhpss-nepal` · Branch: `architecture/v2-immutable-authority` (review artifact, not deployed)

| Field | Value |
|---|---|
| Worktree | `/root/mhpss-nepal-work/v2-authority-redesign` — sole task, confirmed before starting |
| Base | `3cfbe68c18937b7124c7b92d6fe63b4b09bb2cc0` |
| Test-only commit (red) | `d315a61cb8979e098f726745ad89d9476f4c7562` |
| Head (fix, green) | the commit carrying this file; its SHA-256 and SHA-1 are recorded in the kanban completion metadata, so this document does not have to embed its own commit id |
| Production refs | public `68bf197`, form `9032bb7`, hub `ff2d4e2` — unchanged; no push/PR/merge/deploy |
| Worktree | clean after the fix commit |

Status: **DONE - REVIEW ARTIFACT** with three named open questions for Adib (§6).

---

## 1. The safety property

> No document can land in the collection the public reads with suppression disabled.

Enforced at three independent points, each of which alone defeats the confirmed finding:

| # | Where | Rule | Failure mode |
|---|---|---|---|
| A | Publisher (`apps/hub/assets/fb.js` `publish()`) | refuse `docId === "referral_directory"` | referral content cannot reach `public_stats` at all |
| B | Publisher | refuse `body.mode !== "production"` | demonstration/staged output cannot reach `public_stats` |
| C | Publisher | refuse a `suppressed_below` that is missing, non-finite, or below the policy floor 10 | a document cannot declare its own floor away |
| D | Hub UI (`apps/hub/index.html`) | the three-document shelf becomes two documents; the referral-directory row, preview and publish path are removed | the path cannot be chosen in the first place |
| E | Reader (`apps/public/assets/public-read.js`) | a declared `suppressed_below` below the page's own floor is ignored — **defence in depth only** | even a document already in the collection cannot lower the rendered floor |

A, B, C fire **before** the connection and sign-in checks, so they hold in every runtime state
(offline, unconfigured, signed out, signed in). This mirrors the existing `containsRestricted`
guard that the repo already carries.

**The publisher is the fix.** E is stated as defence in depth because a raw value already written
to a collection is exposed to anyone who reads the document directly — a reader-side change cannot
un-expose it.

## 2. The `referral_directory` decision

**Decision taken: remove it from the public publication path entirely** (the most protective of
the available options), rather than inventing a new public presentation for it.

Why: the Hub's own rule in this repository is that referral content must not structurally reach
the public aggregate. `referral_directory` published **organisation × palika names** — a list of
who works where — which is exactly that class. Making it "safer to read" would have meant inventing
a public presentation for referral data that nobody has approved, so the guard removes the path
instead and leaves the destination decision to Adib (§6, Q1).

Consequences, all visible in this diff:

- `PUB_IDS` is `["flood_response", "coordination_full"]`;
- `buildPublicDocs()` no longer builds a `referral` document at all (the `byOP` / `dirRows` block
  and the `referral_directory: referral` key are gone) — so no code path can produce it;
- the `pubDir` checkbox and the `want.push("referral_directory")` branch are removed;
- the referral preview block is removed from the publish preview;
- the publish panel's copy now says why the referral directory is withheld. The referral
  **public** page (`apps/public/referral-directory.html`) is untouched and still reads
  `public_stats/referral_directory`; it will show "nothing published" until Adib decides where
  that content belongs.

## 3. What the fix looks like

```text
apps/hub/assets/fb.js   +18 lines at the top of publish(), before the connection checks
apps/hub/index.html     two-document shelf; referral path, preview and checkbox removed
apps/public/assets/public-read.js   floor = declared >= FLOOR ? declared : FLOOR
```

The publisher's floor constant is `PUBLIC_SUPPRESSION_FLOOR = 10` in `fb.js`, deliberately equal
to the reader's `FLOOR` in `public-read.js`. The number is a **policy minimum, not a new policy**:
10 is the floor the public site already uses and states in its own source note.

## 4. Failing-first — exact commands and observed output

Both runs below are the **same tests**; only the source differs. This is the failing-first
evidence, not a claim.

### 4.1 RED — tests at the test-only commit, source at base

```bash
git stash push -- apps/hub/index.html apps/hub/assets/fb.js apps/public/assets/public-read.js
python3 -m unittest tests.test_publication_privacy_gate tests.test_hub_publish_ui_browser tests.test_public_reader_floor_browser
```

Observed: `Ran 8 tests … FAILED (failures=9)`, including

```text
FAIL: test_disabled_floor_and_nonpublic_modes_cannot_publish … AssertionError: False is not true
FAIL: test_referral_directory_cannot_publish … AssertionError: 'referral_directory' not found in 'not connected'
FAIL: test_hub_does_not_offer_referral_directory_for_publication … 'id="pubDir"' unexpectedly found
FAIL: test_publish_panel_offers_only_the_two_public_aggregates … AssertionError: 1 != 0
FAIL: test_what_the_page_would_publish_is_refused_by_the_real_sink … 'the page sent nothing to publish'
FAIL: test_declared_floor_of_one_cannot_lower_the_page_floor … '6' unexpectedly found in '… PSS 6 … Counts below 1 are not shown.'
```

The last line is the important one: with the base reader, a document declaring
`suppressed_below: 1` renders the below-floor value **6** as itself.

### 4.2 GREEN — at the fix head

```bash
python3 -m unittest tests.test_publication_privacy_gate tests.test_hub_publish_ui_browser tests.test_public_reader_floor_browser -v
```

Observed:

```text
Ran 8 tests in 13.028s

OK
```

Per test:

| Test | What it proves |
|---|---|
| `test_referral_reconciliation_and_restricted_records_cannot_publish` | (pre-existing) restricted records cannot publish — still green |
| `test_disabled_floor_and_nonpublic_modes_cannot_publish` | floors `1` are refused; `demonstration` and `staged` modes are refused, even at a good floor |
| `test_referral_directory_cannot_publish` | `referral_directory` is refused by the sink |
| `test_hub_does_not_offer_referral_directory_for_publication` | the Hub page contains no referral publication path |
| `test_compliant_production_aggregate_passes_privacy_checks` | a compliant document passes the privacy checks and then fails only on "not connected" (so the guard is not a blanket refusal) |
| `test_publish_panel_offers_only_the_two_public_aggregates` | **real browser**: the Publish tab shows exactly `public_stats/flood_response` and `public_stats/coordination_full`; one checkbox each |
| `test_what_the_page_would_publish_is_refused_by_the_real_sink` | **real browser → real sink**: the documents the live page actually builds are captured and fed to the real `fb.js` sink; every one is refused, zero writes |
| `test_declared_floor_of_one_cannot_lower_the_page_floor` | **real browser**: the live public page draws `fewer than 10` and states floor 10, for a document declaring `suppressed_below: 1` |

### 4.3 The original reproduction's publish path

The task requires that *"the original reproduction's publish path no longer permits it"*.
`test_what_the_page_would_publish_is_refused_by_the_real_sink` is that link: it drives the real
Hub page, captures what the real Publish button would hand to `FB.publish()`, and feeds each
captured document to the **real** `fb.js` sink. Observed: **zero writes**, every document refused
on `mode`.

The reproduction itself lives in the audit tree
(`coordination/evidence/layer3-below-floor-reconstruction/`); it models the per-number suppression
class and is not updated by this ticket — that is the sibling ticket `t_f3b83790`. What this ticket
closes is that its output **cannot reach `public_stats`**.

## 5. Verified vs inferred

**Verified (executed in this worktree):**

- Every claim in §4, with the commands above.
- The Hub page in a real headless Chromium shows no referral publication control and refuses to
  publish a demonstration document.
- The live public page in a real headless Chromium ignores a declared floor of 1.
- `public_stats` is still empty. Read-only, aggregate-only REST check, 2026-09-20:
  `HTTP 200`, body `{}`, **0 documents**. No record body, no field value, and no document ID was
  printed, stored or reproduced. No write of any kind was made to any collection.
- Full suite: `python3 -m unittest discover -s tests` → `Ran 114 tests`, 113 pass; the one
  remaining failure and one error are **pre-existing and unrelated** (see §7).

**Inferred, not proven:**

- That the deployed server-side Firestore Rules would also refuse these writes. The Rules are not
  versioned in this repository, so the guard demonstrated here is a **client-side, fail-closed
  control**. It is the same class of control the repo already relies on for restricted records,
  and it is explicitly not a claim about server enforcement.
- That no other publisher exists. Within this repository, `publish()` in `apps/hub/assets/fb.js`
  is the only code that writes to `public_stats` (searched: `apps/hub/assets/fb.js` line 522 is the
  single `setDoc(… "public_stats" …)` call). A caller outside this tree is outside this evidence.

**Residual uncertainty:**

- I did not read back the deployed Rules, so I cannot say whether a direct SDK write to
  `public_stats` from another client would be accepted by the server. This is stated plainly rather
  than glossed: **the guard is a publisher-side control, and the server-side control is unverified.**

## 6. Open questions for Adib (the choices this ticket deliberately did not invent)

- **Q1 — Where does the referral directory go?** The Hub no longer publishes it to `public_stats`.
  The public referral page still reads `public_stats/referral_directory` and will show "nothing
  published". Options: (a) a separate non-public coordinator-only collection that the public page
  does not read; (b) a reviewed, redacted public presentation that is decided on its merits;
  (c) withdraw the partner-directory section from the public page for the trial. **Implemented
  now: none of these — the content simply has no public path.**
- **Q2 — Is 10 the Ministry/WHO-approved floor for public counts?** The guard enforces the floor
  the public site already used and stated. If the approved floor differs, it is a one-line change
  in `fb.js` **and** `public-read.js` together, and it is a policy decision, not a code decision.
- **Q3 — Does public publication stay held until the review?** The guard does not itself block
  publication of a compliant `production` document; the standing rule ("nobody presses Publish")
  still holds. If publication is to be blocked in code until the review, that is a further,
  explicit decision.

## 7. Pre-existing failures (not caused by this change, not fixed here)

`tests/test_third_review.py::LocalQAServerSafetyTests::test_browser_helpers_serve_the_application_root_from_any_cwd`
fails (hub helper) / errors (public helper) at **clean base `3cfbe68` with no local changes** —
confirmed by stashing all changes and re-running. The helper reports two text blocks on
`forms.html` and `access.html` that it calls "not flush", both of which quote a local `404`
document; it is unrelated to the publication shelf. Left untouched: this ticket is the guard only.
Scope note: the sibling redaction ticket is `t_f3b83790`; referral reconciliation (`t_5a3012fa`) and
the referral safeguarding gate (`t_ed5ad1cf`) were not touched.
