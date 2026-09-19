# MHPSS Nepal V2 executable contract foundation

Implementation checkpoint: **DONE — REVIEW ARTIFACT** candidate. Independent verdict: **HELD** after two adversarial review rounds. Local-only, synthetic-data reference. Not production-ready, not integrated, not deployed.

The contracts below state the required V2 invariants. The current executable
candidate does not yet satisfy every invariant under novel corruption and
interleaving probes. The preserved blockers in `V2-EVIDENCE-LEDGER.md` govern;
passing the committed suite does not override them.

## Scope and authority

This foundation turns the approved 19 September 2026 architecture direction into executable Python standard-library contracts. It does not select a production runtime, alter the current applications, write to Firebase/Firestore, or establish institutional policy.

The SQLite modules model transaction, crash, idempotency, projection, and reconciliation semantics that a later IndexedDB client and institutionally approved ingestion datastore must preserve. SQLite is not the selected browser or production datastore.

## 1. Immutable event envelope

Contract version: `mhpss.event/1.0`.

Required fields:

- `contract_version`
- `schema_name`
- `event_id`
- `event_type`: `submission`, `correction`, or `void`
- `stream_id`
- `revision`
- `predecessor_event_id`
- `occurred_at`
- `client_version`
- `release_id`
- `duplicate_fingerprint`
- `payload`
- `provenance`

Rules:

1. Every independent submission gets a random canonical UUIDv7 `event_id`. Identical content remains two events.
2. Retry sends the byte-identical stored envelope with the same `event_id`.
3. A new stream begins at revision 1 with `stream_id == event_id` and no predecessor.
4. A correction or void is a new immutable event with a new `event_id`, the original `stream_id`, revision exactly current revision plus one, and the current event as predecessor.
5. `duplicate_fingerprint` is a non-unique data-quality signal. It cannot select identity, authorize overwrite, or merge events.
6. Legacy identity is retained only in `provenance`, together with source dataset, source row, and source checksum. It is never a V2 primary key.
7. Canonical JSON is UTF-8 with sorted keys, compact separators, finite numbers, unique keys, strict fields, and bounded bytes/depth/nodes. Acceptance stores and acknowledges the exact canonical bytes.
8. Event creation requires a verified runtime proof covering exactly Form, Hub, and contracts at one supported `release_id` and contract version. Mixed or incomplete runtime components fail before identity allocation.

The executable reference selects UUIDv7 and exact canonical UTF-8 bytes so tests can run. Institutional approval of those choices remains blocked below.

## 2. Sync state machine and frontend interface

Evidence states are separate and cannot be skipped:

| State | Required evidence | Permitted interface claim |
|---|---|---|
| `created_memory_only` | Page-memory event only | Not saved |
| `durable_queued` | Source and exact outbox bytes committed together | Saved on this device and queued |
| `in_flight` | Transmission attempt started | Sending; acknowledgement pending |
| `retryable_failure` | Durable obligation retained after failure | Still queued; do not resubmit or clear storage |
| `server_acknowledged` | Receipt plus read-back of the exact accepted body | Received by the server for this exact revision |
| `conflict_recovery_required` | Receipt/body mismatch or identity conflict | Do not resubmit or clear; export recovery evidence |
| `projected_reconciled` | Current projection reconciled to the accepted event | Included in the reconciled dashboard projection |
| `reviewed_accepted` | Explicit review decision | Reviewed and accepted |

Frontend preview lanes consume this state/message contract. They must not claim “saved”, “sent”, “received”, “included in dashboard”, or “reviewed” at a weaker state. They must not expose a canonical-write API, derive identity from content, perform destructive correction, or maintain independent KPI formulas.

## 3. Transactional outbox and crash boundary

The local reference transaction atomically creates:

- one immutable source event row;
- one exact-byte outbox row with the same identity, digest, length, and order.

Crash invariants:

- termination before commit leaves neither source nor outbox;
- termination after commit leaves both and retry reuses the identity;
- source bytes and outbox bytes cannot diverge;
- a retry after verified compaction cannot resurrect or requeue a terminal event;
- pending, conflict, or unverified obligations block clear;
- clear and bounded compaction remove payload bytes only for acknowledged events with durable receipts;
- receipt/digest evidence remains after payload compaction.
- identity or acknowledgement mismatch creates durable conflict evidence, preserves the attempted bytes, and requires an explicit recovery action;
- retry, status, clear, and compaction revalidate source, outbox, receipt, acknowledgement, digest, length, and terminal-state parity before trusting or deleting payloads.

The reference uses SQLite `BEGIN IMMEDIATE`, foreign keys, WAL, and `synchronous=FULL`. A browser implementation must provide equivalent semantics in one IndexedDB transaction. Separate source and queue writes do not satisfy this contract.

## 4. Ingestion, idempotency, acknowledgement, and errors

Only an ingestion boundary may write canonical V2 events. A collection client receives a transport interface; it receives no canonical datastore mutation capability.

Acceptance is one transaction covering immutable event bytes, projection update, acknowledgement, and applicable DQ work. Retry behavior:

- same `event_id` + same exact body: return the committed acknowledgement; do not append;
- same `event_id` + different body: retain the accepted body, durably record conflict evidence, and return `EVENT_ID_BODY_CONFLICT`;
- stale, gapped, or wrong-predecessor correction: reject with `STALE_OR_GAPPED_REVISION`; never roll back the projection;
- malformed, duplicate-key, non-finite, oversized, noncanonical, or incompatible envelope: reject with `INVALID_ENVELOPE`; never partially project.

Acknowledgement contract: `mhpss.ack/1.0`, status, event identity, exact body SHA-256, exact byte length, canonical sequence, and contract version. The client may transition to acknowledged only after a separate canonical read-back body matches its stored exact digest and length.

Reserved production error classes must remain explicit when a runtime is selected: validation/incompatible version, identity conflict, stale revision, authorization, rate/resource limit, retryable dependency failure, and internal failure. The local reference implements the contract-relevant validation, conflict, and revision classes; it does not invent production authentication or retry policy.

## 5. Projection, correction, DQ, and reconciliation

- Accepted raw event bytes are append-only and immutable.
- Current projection advances only through exact predecessor and revision lineage.
- Stale or out-of-order events cannot select a winner by arrival order.
- Duplicate fingerprints can open idempotent `POSSIBLE_DUPLICATE` DQ items, but both events and projections remain distinct.
- DQ evidence records the rule version and evidence digest. Domain rule catalogue, severities, ownership, and resolution authority remain blocked decisions.
- Reconciliation is read-only. It compares client receipt identities/digests with canonical events and reports machine-readable differences such as missing canonical event, digest mismatch, and orphan projection. It never averages or silently repairs discrepancies.
- Reconciliation requires a complete, unique receipt set, checks both client→canonical and canonical→client directions, validates each current projection against the latest accepted event, and includes the normalized receipt set in a single-snapshot evidence digest.
- Analytics snapshot and indicator calculation are outside this foundation. A future engine must use versioned rules, atomic snapshots, freshness/provenance, and accepted-event reconciliation.

## 6. Cache and mixed-version contract

A deeply immutable paired release manifest binds `release_id`, `contract_version`, `cache_version`, every unique asset path, byte length, and SHA-256 digest. Verification rejects malformed manifests and missing, extra, tampered, truncated, or swapped cache entries. Runtime Form, Hub, and contract components must share one complete supported release and contract version before an event can be created.

This is an executable integrity contract, not a modified service worker or deployment. Trusting/authenticating the release manifest and selecting last-known-good fallback remain blocked decisions.

## 7. Executable tests

Run:

```bash
python3 -m unittest discover -s tests/v2_contract -p 'test_*.py' -v
```

The synthetic suite covers:

- the known V1 FNV-1a identity collision and distinct V2 identities;
- stable retry identity and legacy provenance;
- strict envelopes, correction lineage, and malformed input;
- source/outbox termination immediately before and after commit;
- ingestion termination immediately before and after commit;
- idempotent retry, exact read-back acknowledgement, and same-ID/different-body conflict;
- stale/out-of-order correction rejection and immutable current projection;
- fail-closed clear, terminal retry, and bounded compaction;
- DQ candidate creation without identity merge;
- read-only reconciliation and digest mismatch reporting;
- cache content digests and mixed release/version rejection;
- truthful frontend sync transitions and prohibited shortcuts.

All fixtures are synthetic. Crash tests use child-process termination rather than caught exceptions.

## 8. BLOCKED — DECISION

No implementation may infer or silently settle these dependencies:

1. **BLOCKED — DECISION:** institutional system owner, data controller, approver, and operational administrator.
2. **BLOCKED — DECISION:** production Firebase/GCP ownership, billing, authoritative Firestore Rules, indexes, environments, and backup capability.
3. **BLOCKED — DECISION:** production ingestion and analytics runtimes and service identities.
4. **BLOCKED — DECISION:** storage, retention, conflict-evidence, compaction, backup, restore, disaster-recovery, and incident policies.
5. **BLOCKED — DECISION:** UUIDv7 institutional approval, stream allocation authority, and clock/entropy operational policy.
6. **BLOCKED — DECISION:** canonical-byte specification approval and supported envelope/client/release compatibility matrix.
7. **BLOCKED — DECISION:** duplicate-fingerprint fields, normalization, privacy constraints, and versioning authority.
8. **BLOCKED — DECISION:** legacy dataset/row identity, changed-row behavior, migration acceptance, and V1 cutover authority.
9. **BLOCKED — DECISION:** stale/gapped/forked correction policy beyond the reference’s safe rejection; resolution authorization.
10. **BLOCKED — DECISION:** DQ rules, severities, workflow, owners, and eligibility for projection/analytics.
11. **BLOCKED — DECISION:** reconciliation authority, cadence, tolerances, and definition of clean-with-history.
12. **BLOCKED — DECISION:** envelope/outbox/resource limits for field and production operation.
13. **BLOCKED — DECISION:** trusted release-manifest root, cache fallback, atomic activation, paired rollback, staging domain, and rollout criteria.
14. **BLOCKED — DECISION:** Nepal HMIS/DHIS2 metadata and acceptance owner; OCHA format/delivery/acceptance owner; FHIR requirements.
15. **BLOCKED — DECISION:** identity/role model, post-trial data classification/publication rules, indicator definitions, and approval authority.

## Completion boundary

Passing these tests proves an executable contract foundation only. It does not prove IndexedDB behavior in supported browsers, a production ingestion service, authorization, operational monitoring, analytics, migration, backup/restore, institutional acceptance, or deployment safety. The maximum classification is **DONE — REVIEW ARTIFACT**.
