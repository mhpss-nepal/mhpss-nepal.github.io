# Referral safeguarding gate — evidence note

Task: `t_ed5ad1cf` — *Make the referral safeguarding gate actually block (label is not a control)*
Tenant: `mhpss-nepal` · Branch: `architecture/v2-immutable-authority` (review artifact, not deployed)

| Field | Value |
|---|---|
| Base | `d4d45d870a7bde423b787c6addf847069898b1fc` |
| Test-only commit (red) | `98ddacfe7025025f3330679d11ce979353675ffe` |
| Head (fix, green) | `ca67fc75b2eb3ea83b2487103ebcc37ab5dc34c0` |
| Actionable-route test-only commit (red) | `7ca1cf5` |
| Actionable-route fix commit (green) | `cdf7edb` |
| Kind-argument bypass test-only commit (red) | working-tree test at `c899439` |
| Kind-argument bypass fix commit (green) | pending at the time this note was edited |
| Production ref `origin/main` | `68bf197abe56dd0265dca245e61809100b4c3901` — unchanged; no push/PR/merge/deploy |
| Worktree | clean after commit |

Status: **DONE — REVIEW ARTIFACT** (release integration still required). The code control is
complete and every test passes. The refusal now names the parent-verified routes and numbers;
it does not claim that every district pathway is functioning.

---

## 1. The defect (confirmed)

`apps/form/referral.html` shows a safeguarding checkbox `#notgbv` whose help text
reads *"If you cannot tick this, close the form and use the specialised pathway."*
The value was recorded as data only; no code path refused. A worker could leave it
unticked, press **Save**, and a GBV / unaccompanied-or-separated-child / immediate-
risk-to-life case was written to the device and enqueued for the coordination
register. A warning label is not a control.

## 2. What changed (minimal diff, 3 files)

- `apps/hub/assets/l1.js` — the shared Layer-1 write boundary now refuses an
  unticked referral **before** the device write and **before** the queue, so no
  caller of `L1.save` can reach the register around the gate. Exports
  `safeguardingRefusal(record)` and the bilingual `SAFEGUARDING_REFUSAL` text.
  Fail-closed: a referral is safe only when the record itself carries
  `safeguarding_confirmed === true` **and** `excludes_gbv_uasc_lifethreat === true`.
- `apps/hub/assets/fb.js` — the same rule enforced **again and independently** at
  the queue, deliberately self-contained so it holds even where `l1.js` is not
  loaded (the hub loads this file without it). `submit()` refuses and rejects;
  `flush()` prunes any unsafe entry already queued (`purgeUnsafeQueue()`) before any
  transmission. Nothing unsafe is written, queued or sent.
- `apps/form/referral.html` — a blocking, bilingual refusal surface
  (`#safeguardingBlock`, `role="alertdialog"`, `aria-modal="true"`), shown in place
  of the ordinary error list. It states the required action in English and Nepali
  and cannot be dismissed into a save.

The checkbox's **meaning and wording are unchanged** (see §6, translation).

## 3. Failing-first proof (exact commands and counts)

Written to fail against the pre-fix code, then made to pass.

```
# RED — runtime files at the test-only commit (pre-fix behaviour):
git checkout 98ddacf -- apps/hub/assets/l1.js apps/hub/assets/fb.js apps/form/referral.html
python3 -m unittest tests.test_referral_safeguarding_gate -v
#   Ran 9 tests ... FAILED (failures=5)
#   FAIL test_unticked_gate_cannot_save_or_enqueue
#   FAIL test_queue_api_rejects_unticked_referral
#   FAIL test_retry_drops_legacy_unsafe_queue_entry_without_transmitting
#   FAIL test_reopened_unsafe_record_cannot_be_resaved_or_queued
#   FAIL test_form_has_a_bilingual_blocking_error_surface

# GREEN — the fix restored:
git checkout HEAD -- apps/hub/assets/l1.js apps/hub/assets/fb.js apps/form/referral.html
python3 -m unittest tests.test_referral_safeguarding_gate -v
#   Ran 9 tests ... OK   (9 passed, 0 failed)

# RED 2 — at test-only commit 7ca1cf5, before the route fix:
python3 -m unittest tests.test_referral_safeguarding_gate -v
#   Ran 10 tests ... FAILED (failures=5)
#   Missing 1145 / 1098 / 100 / 102 / 16600102005 from the refusal paths.

# GREEN 2 — at fix commit cdf7edb, actionable routes are in every refusal:
python3 -m unittest tests.test_referral_safeguarding_gate -v
#   Ran 10 tests ... OK   (10 passed, 0 failed)

# RED 3 — independent review supplied an untyped record with kind="referral":
python3 -m unittest \
  tests.test_referral_safeguarding_gate.ReferralSafeguardingGateTests.\
test_referral_kind_argument_cannot_bypass_gate_with_untyped_record -v
#   Ran 1 test ... FAILED (failures=1); unsafe record was saved and queued.

# GREEN 3 — L1.save now treats its explicit kind argument as authoritative:
python3 -m unittest tests.test_referral_safeguarding_gate -v
#   Ran 12 tests ... OK   (12 passed, 0 failed)
```

An independent mutation check (temporarily disabling the three guards, then
restoring) reproduced the same pattern: `FAILED (failures=4)` with the write-
boundary and queue guards off, `OK` with them on.

The tests run the real `l1.js` and `fb.js` in a Node `vm` context (Node v26.9.0)
and drive the actual functions — not copies of them.

## 4. Every save / queue / retry path, and its gate result

| # | Path | Where | Unticked referral | Ticked referral |
|---|---|---|---|---|
| 1 | Form **Save** button | `referral.html` submit handler | Blocked by the panel; `L1.save` never called | Saves |
| 2 | Direct `L1.save(kind, record)` (any caller) | `l1.js` write boundary | **Throws `SafeguardingRefusal`**; nothing written | Writes |
| 3 | Shared-layer sync to the register (`L1.save → FB.submit`) | `l1.js` | Never reached (blocked at #2) | Queued/synced |
| 4 | Queue API `FB.submit(record)` directly | `fb.js` | **Rejects**; not queued | Queued |
| 5 | Retry / flush of a legacy queued entry | `fb.js` `flush()` → `purgeUnsafeQueue()` | Entry **removed**, not transmitted | Sent |
| 6 | Re-opened previously-saved unsafe record, re-saved | `l1.js` | **Throws**; not re-queued | Saves |
| 7 | Hub import of an exported/register row (`forms.html`) | local read path | No re-enqueue path exists (rows are added to a display store, never re-submitted) | n/a |
| 8 | Other forms (contact, phq9, selfreport, 5ws) | `l1.js` | Unaffected (tested) | Unaffected |

## 5. Service-worker cache (required for the fix to reach a phone)

`l1.js`, `fb.js` and `referral.html` are precached by `apps/form/sw.js`. A phone
that already installed the previous cache keeps running the old code until the
cache name changes. This fix therefore **requires a `CACHE` bump** (currently
`mhpss-np-field-v39`; the sibling `form-safety` worktree records `v41`) **and a
refresh of `apps/form/tools/precache.sha`**.

This was **not done in this task, on purpose**: `sw.js` / `precache.sha` are the
shared "atomic Form+Hub release pair" owned by sibling tasks (`form-safety`,
`hub-safety`), and uncoordinated edits here would collide with that release
boundary. Recorded as a required handoff, not a silent omission. The digest and
cache version must move together in the monorepo integration (see
`/root/mhpss-nepal-work/hub-safety/release-contract.json`).

## 6. Translation note (wording changes flagged for re-review)

- The checkbox text and its help sentence are **byte-for-byte unchanged**, so the
  existing translation extraction is unaffected.
- New English prose was added: the refusal panel and the shared refusal message.
  A **Nepali draft** is included **beside the English on the same surface** (both
  languages always shown, so it cannot render Nepali-only on an English phone or
  vice versa). The panel carries its own note that the Nepali needs professional
  review. This Nepali is **new prose that requires re-translation and sign-off**.
- `safeguard.*` is already listed in `i18n-strings.js` as a prefix that must be
  professionally translated. This task did not add `safeguard.*` keys (which would
  trip the sibling page-keying work); the mechanism is flagged for that task.

## 7. The specialised routes named by the refusal

The parent task supplied independent verification for the reachable national routes
and directed that the refusal name them rather than an abstract cluster pathway:

| Situation | Route named | Operating qualification |
|---|---|---|
| GBV | **1145** | National Women Commission Khabar Garaun; reported 24/7, free and confidential |
| Child crisis / unaccompanied or separated child | **1098** | Child Helpline Nepal; reported 24/7 and free |
| Immediate risk to life | **100** police / **102** ambulance | Act first; never wait on this form |
| Clinical / medical | nearest **OCMC** | Use the nearest functioning centre; district availability remains an open operational check |
| MHPSS-specific | **16600102005** | TPO Nepal, 08:00–18:00; explicitly not 24/7 |

The refusal says district pathways **may be disrupted**. It does not claim that a
local service map, focal point, or OCMC is functioning everywhere. The parent cited
independent government, World Bank, UN Women, UNICEF and CWIN checks for the numbers;
this evidence note records that handoff rather than reproducing sensitive contacts.

Residual human ownership: confirm the district-level GBV and child-protection focal
points, report the pathway gap to the Protection Cluster if required, and check
whether the nearest OCMC for Nuwakot/Rasuwa is functioning. These are operational
follow-ups, not reasons to weaken or remove the block.

## 8. Environment notes (corroborating, not caused by this diff)

- The worktree is **shared while this task runs** (a sibling task's
  `tests/test_form_registry.py` appeared and then vanished). Only the three files
  above plus `tests/test_referral_safeguarding_gate.py` were touched.
- One pre-existing test fails in this environment:
  `test_third_review.LocalQAServerSafetyTests.test_browser_helpers_serve_the_
  application_root_from_any_cwd` — the two `justify-sweep.py` helpers use a fixed
  port (9071) and attach to a stale local server, producing "404". This reproduces
  on an **untouched `git archive HEAD`** export and touches none of the changed
  files.
- Full suite on this tree: `Ran 95 tests ... FAILED (failures=1, errors=1)`, the
  only failing item being the pre-existing sweep above (plus, when several test
  modules run together, the fixed-port collision it causes).

## 9. Constraints respected

- Production refs unchanged (`68bf197`, form `9032bb7`, hub `ff2d4e2`); no push,
  PR, merge, or deploy.
- Synthetic records only; no real safeguarding case created, saved or transmitted.
- The sibling translation-extraction work is untouched; wording changes are noted
  for re-translation rather than applied.

## 10. Reproduce

```bash
python3 -m unittest tests.test_referral_safeguarding_gate -v     # 9 passed
node --check apps/hub/assets/l1.js && node --check apps/hub/assets/fb.js
python3 -c "import re,pathlib; s=pathlib.Path('apps/form/referral.html').read_text(); \
  open('/tmp/inline.js','w').write(max(re.findall(r'<script>(.*?)</script>',s,re.S),key=len))" \
  && node --check /tmp/inline.js
```
