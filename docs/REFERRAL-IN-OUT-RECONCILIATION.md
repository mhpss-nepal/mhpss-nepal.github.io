# Referral IN/OUT reconciliation — review design

Status: **DONE — REVIEW ARTIFACT**. Synthetic data only; local-only prototype; not integrated or deployed.

## 1. Boundary and risk statement

This is an analytical data-quality operation over immutable V2 referral events. It does not rewrite, delete, join, or select a canonical person identity. Every referral event and stream remains intact. A duplicate candidate is evidence for review, never permission to overwrite a projection. The prototype intentionally does **not** invent a standalone resolution format: under the existing V2 contract, human acceptance must be expressed through an accepted correction/void event and appended by the canonical `IngestStore.resolve_dq()` authority path. Reversal therefore requires another accepted correction/void and immutable resolution history, not deletion. The richer three-decision workflow below remains a design requirement whose production event schema/authorization is **BLOCKED — DECISION**.

The contact code is a **pseudonym, not an anonymous token**. It is derived on the handset from initials, year of birth, sex, and municipality. Those inputs vary little, so a holder of a candidate-name list can test guesses. Without a server-held secret, the code retains residual re-identification risk. Reconciliation must not be presented as anonymous or as definitively de-duplicated.

A referral collection is a **restricted list of referred persons**, closer to a patient list than coordination data. The actual `FB.publish()` public sink now recursively refuses `kind: referral`, `kind: phq9`, and restricted/clinical/safeguarding privacy classes before connection or authentication checks. A Node runtime test drives that real sink and proves zero writes. Server Rules remain unversioned, so this is a blocking client control in the review artifact, not a claim of production server enforcement.

Two error directions remain harmful:

- False merge: two people treated as one, understating need. Exact matching can still make this error where two people share a derived code; contradictory attributes therefore block the match, but absence of contradiction is not proof of identity.
- Missed match: one person remains as two records, overstating need. Typing variation and missing attributes make this likely; possible matches are exposed as DQ signals where safe, never silently accepted as two definitely different people.

## 2. Executable taxonomy

| Code | Trigger | Automatic count action | Review action |
|---|---|---|---|
| `REFERRAL_MATCH_EXACT` | Exactly one `IN` and one `OUT`, identical valid code, no contradictory shared attributes | Two records contribute one to the restricted resolved-person figure | Rule result remains auditable; no canonical mutation |
| `REFERRAL_POSSIBLE_MATCH_QUEUED` | Opposite directions, code differs by exactly one character, same comparison cell, cell not small | Records remain separate | Coordinator reviews; never auto-merged |
| `REFERRAL_UNMATCHED_OUT` | Valid OUT not in an exact pair | One | Remains valid; possible failed match is additionally a DQ signal |
| `REFERRAL_UNMATCHED_IN` | Valid IN not in an exact pair | One | Same as above |
| `REFERRAL_DIRECTION_CONFLICT` | Same valid code appears more than once without exactly one IN + one OUT, or direction is invalid | Each record remains separate | Correct or explicitly retain with evidence |
| `REFERRAL_SAME_CODE_ATTRIBUTE_CONFLICT` | Same code but sex, age band, or district contradicts; also used for referral/contact cross-form disagreement | Each referral record remains separate | Inspect source evidence; do not infer identity |
| `REFERRAL_MALFORMED_CODE` | Code fails `^NP-[0-9A-Z]{5}-[0-9A-Z]{5}$` | One record, excluded from matching | Correct through a V2 correction event |
| `REFERRAL_SMALL_CELL_SUGGESTION_SUPPRESSED` | Near-code pair occurs in a small comparison cell | Records remain separate | No pairwise suggestion shown; only suppression signal |

The prototype's near-match rule is deliberately narrow: equal-length valid codes with Hamming distance one, opposite directions, and the same `(district, site_from)` cell. It performs no name, birth-date, phone, or free-text matching.

## 3. Small-cell rule

A near-match suggestion is suppressed when its `(district, site_from)` comparison cell contains fewer than **5 distinct valid contact codes**, or either cell field is missing. The threshold is fixed in the prototype and cannot be weakened by a caller. It is a conservative design choice, not an approved publication or k-anonymity standard; institutional privacy owners must approve or replace it in a reviewed release. Suppressed output omits both candidate codes from the entire result, including companion unmatched items, and exposes only immutable record IDs, non-code reviewer attributes, cell size, threshold, and the suppression code.

Reason: in a small village or site, initials, year of birth, sex, and municipality can collide. Showing a near-code candidate makes an unsafe identity suggestion precisely where there are too few alternatives. Suppression trades more missed matches/overcount risk for lower false-merge and re-identification risk.

## 4. Count semantics and non-additivity

The prototype emits two restricted internal measures:

- `raw_referral_records`: immutable referral events in the analytical input.
- `internal_referral_persons_resolved`: raw records minus one for each unambiguous exact IN/OUT pair. It is a conservative analytical view, not a definitive unique-client count.

Possible matches, suppressed suggestions, malformed records, direction conflicts, and attribute conflicts remain separate until an explicit accepted resolution is applied by a future reviewed projection. They are not silently collapsed.

No referral-person count is published. Referral records and service-contact records are different event types and are not additive. A matching contact code across the two forms is only a cross-form DQ check: the service contact does not add to or subtract from the referral-person figure. Likewise, referral-person counts must not be summed with 5Ws reach, service contacts, or non-additive imported reach measures.

### Worked examples (Adib's four scenarios)

| Scenario | Raw referral records | Restricted resolved-person count | DQ state |
|---|---:|---:|---|
| One OUT and one IN, same valid code, compatible attributes | 2 | 1 | Exact pair |
| One OUT only | 1 | 1 | Unmatched OUT; acceptable single-sided record |
| One IN only | 1 | 1 | Unmatched IN; acceptable single-sided record |
| One OUT and one IN for the same real person but mistyped codes | 2 | 2 until reviewed | Possible-match queue when cell ≥5; suppressed signal when cell <5. This is not “fine”: it is potential overcount |

## 5. Reviewer workflow

1. The coordinator sees the DQ code, immutable event IDs, directions, source form(s), compatible non-identifying attributes, and rule version/basis. In an eligible possible-match cell, the two pseudonymous codes may be shown only in the restricted reviewer surface. In a small cell, the pairwise code suggestion is suppressed.
2. The coordinator chooses `same person`, `separate people`, or `insufficient evidence`; the interface must never offer an automatic “best match”. Actor, time, reason, and reviewed evidence are mandatory design fields.
3. Under the currently executable V2 contract, a count-affecting acceptance requires an accepted correction or void of the flagged event, then `IngestStore.resolve_dq()` appends the immutable canonical DQ-resolution record. It does not edit either original referral event or make either event ID canonical for the other.
4. Reversal must be another accepted correction/void and append-only resolution history. The existing prototype does not yet encode decision labels, actor/reason, or supersession chains; those remain **BLOCKED — DECISION**, rather than being simulated by an unattached dictionary.
5. Production DQ ownership, authorization, resolution-event schema, retention, and reconciliation cadence remain **BLOCKED — DECISION** under `docs/V2-CONTRACTS.md`.

## 6. Cross-form contact-code behavior

`contact.html` creates the pseudonym and stores it on `service_contact`; `referral.html` accepts the same code. The reconciler may compare exact codes across those forms for DQ only:

- same code and compatible attributes: informational cross-form link signal, not a person merge and not a count change;
- same code with contradictory sex, age band, or district: `REFERRAL_SAME_CODE_ATTRIBUTE_CONFLICT`, review required, no count change;
- near code across forms: no suggestion. The task authorizes near-code review only for IN/OUT referral reconciliation, not general identity linkage.

## 7. V2 contract fit

- Input is the current projection derived from rehashed immutable referral streams.
- Event ID and `stream_id` remain canonical identities; contact code is never substituted for either.
- Duplicate/contact fingerprints and code comparisons identify candidates only.
- DQ work is derived and reproducible; a resolution is a new immutable authority event.
- Reconciliation never repairs or averages records silently.
- A correction to a referral must use the V2 correction lineage; it must not mutate the original event.

## 8. Verification evidence

Failing-first test was run before the module existed:

`python3 -m unittest tests.test_referral_reconciliation -v`

Result: expected RED, `ModuleNotFoundError: No module named 'referral_reconciliation'`.

After implementation and the first independent review correction, the focused commands cover exact pair, possible match queued/not merged, lone OUT, lone IN, direction conflict, contradictory attributes, malformed and noncanonical code, duplicate event identity, fixed/missing-cell suppression with whole-result redaction, cross-form disagreement, restricted classification, and the real `FB.publish()` public sink. Existing V2 tests separately prove that DQ resolution requires an accepted correction/void and remains in immutable authority history.

Production form files are unchanged. This artifact does not push, merge, deploy, or change production references (`68bf197`, `9032bb7`, `ff2d4e2`).
