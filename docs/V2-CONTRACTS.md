# MHPSS Nepal V2 immutable-authority contract

Implementation checkpoint: **DONE — REVIEW ARTIFACT candidate**. Local-only, synthetic-data reference. Not production-ready, not integrated, not deployed.

## Scope and design decision

The held `mhpss.event/1.0` artifact trusted mutable source/outbox rows, acknowledgements, receipts, and projection metadata in different operations. V2 replaces that model with one byte-rehashed, append-only authority in each trust domain:

- the device authority is a hash-chained commit log for durable commit, conflict, audited recovery, acknowledgement, and compaction events, with payload bytes held only as a recoverable materialization;
- the ingestion authority is a hash-chained canonical event log containing exact event bytes; lineage, acknowledgement, current projection, DQ state, and reconciliation are derived by replaying and rehashing this log;
- projection caches and retained payloads are non-authoritative materializations and never authorize transitions;
- every authority read validates contiguous sequence, previous-record hash, current-record hash, canonical JSON, exact retained bytes, and domain semantics before making a claim or deleting bytes.

SQLite is an executable transaction/crash model, not a selected browser or production datastore. A future IndexedDB and institutionally selected server runtime must preserve the same authority and transaction semantics.

## 1. Event envelope and trusted identity

Contract version: `mhpss.event/2.0`.

Required fields are `contract_version`, `schema_name`, `event_id`, `event_type`, `stream_id`, `revision`, `predecessor_event_id`, `occurred_at`, `client_version`, `release_id`, `release_manifest_sha256`, `duplicate_fingerprint`, `payload`, and `provenance`.

Rules:

1. Public event-creation APIs do not accept `event_id`; the trusted boundary allocates a random UUIDv7.
2. A retry reuses the byte-identical persisted envelope, not the creation API.
3. A submission begins revision 1 with `stream_id == event_id`; a correction or void gets a new trusted identity and names its exact predecessor.
4. Legacy identity remains provenance only and cannot become canonical identity.
5. Canonical JSON is strict finite UTF-8 with sorted keys, compact separators, unique keys, and enforced byte/depth/node bounds.
6. Every event binds `release_manifest_sha256`, not only a release label.
7. Creation requires an opaque proof emitted only after the complete trusted manifest, every cached asset, and Form/Hub/contracts component metadata are verified together.

Institutional approval of UUIDv7, entropy/clock operations, and canonical byte rules remains blocked below.

## 2. One executable state vocabulary

`packages/contracts/sync_states.py` is the sole vocabulary exported to the frontend contract:

| State | Required evidence | Permitted interface claim |
|---|---|---|
| `created_memory_only` | Page-memory event only | Not durably saved |
| `durable_queued` | Rehashed commit record and exact retained payload | Saved on this device and queued |
| `in_flight` | Transmission attempt started | Sending; acknowledgement pending |
| `retryable_failure` | Durable obligation retained after failure | Still queued |
| `server_acknowledged` | Rehashed acknowledgement event and exact canonical read-back | Received for this exact revision |
| `conflict_recovery_required` | Conflict, corruption, missing recovery copy, or invalid authority | Stop; export evidence; do not clear |
| `projected_reconciled` | Projection reconciled to canonical authority | Included in reconciled projection |
| `reviewed_accepted` | Explicit review decision | Reviewed and accepted |

No alternate status identifier is emitted by the outbox. Corrupt or malformed evidence returns `conflict_recovery_required`; status inspection does not crash.

## 3. Device commit-log authority

A save transaction atomically appends one `device_commit` authority record and one exact recoverable payload. The record binds identity, SHA-256, byte count, and contract version. Retry and status rehash the complete log and exact retained bytes.

Conflict rules:

- identity/body or acknowledgement/read-back mismatch appends a `device_conflict` record;
- `incoming_sha256` is computed over the exact retained `incoming_body` bytes;
- conflict is sticky; later valid acknowledgement cannot bypass it;
- only `record_recovery(actor, reason)` can append an audited recovery event against the latest conflict hash;
- an acknowledgement after recovery appends a new authority event; previous conflict and recovery evidence remain immutable.

Clear/compaction rules:

- every commit in the authority, including already compacted commits, is validated before any later clear;
- every obligation must derive as acknowledged, with no unresolved conflict;
- a payload can be removed only in the same transaction that appends bounded `device_compaction` evidence binding its commit and acknowledgement record hashes;
- missing one of multiple payload copies is a corruption, not permission to remove the remaining copy;
- corrupted or oversized compaction metadata blocks all deletion;
- selective/asymmetric compaction is rejected by the reference; one atomic boundary clears all verified payloads or none.

Process-termination failpoints before and after save, acknowledgement, and clear commits prove either no effect or a complete idempotently recoverable effect.

## 4. Canonical ingestion authority

Only the ingestion boundary appends canonical records. Browser direct canonical writes and V1/V2 dual-write are prohibited.

One canonical-event authority record embeds the exact canonical event bytes plus their SHA-256 and length. Acceptance validates the pre-existing log, derives lineage from its rehashed bytes, appends the event, revalidates the resulting log, refreshes the projection cache, and returns a derived `mhpss.ack/2.0` acknowledgement.

Retry rules:

- same `event_id` and exact bytes: revalidate the full authority and derive the same acknowledgement;
- same `event_id` and different bytes: append immutable conflict evidence and return `EVENT_ID_BODY_CONFLICT`;
- stale, gapped, wrong-predecessor, schema-changing, or forked successor: reject with `STALE_OR_GAPPED_REVISION`;
- malformed, duplicate-key, non-finite, oversized, noncanonical, or incompatible envelope: reject with `INVALID_ENVELOPE`.

The mutable projection cache is disposable. It cannot authorize a successor and is refreshed from rehashed immutable events after acceptance.

## 5. Projection, DQ, and reconciliation

- Lineage and current projection are derived from contiguous exact predecessor/revision chains in immutable event bytes.
- Forks, gaps, duplicate roots, duplicate canonical identities, malformed records, and record-hash mutations fail closed.
- Duplicate fingerprints remain non-unique DQ signals and never select identity or overwrite canonical events.
- DQ resolution is an immutable authority event naming an accepted correction.
- Reconciliation rehashes canonical authority first, normalizes receipts into deterministic `(event_id, body_sha256)` order, reports duplicate receipts independently of input order, checks both client→canonical and canonical→client directions, and validates all projection-cache keys and values.
- Canonical body/digest mutation returns `AUTHORITY_INTEGRITY_FAILURE`; unrelated or miskeyed projection cache rows return `UNRELATED_PROJECTION`.
- Reconciliation never silently repairs or averages discrepancies.

## 6. Trusted release manifest

`mhpss.release/2.0` binds `release_id`, `contract_version`, `cache_version`, and every asset path/length/SHA-256.

Asset paths must be absolute, NFC-normalized, unencoded canonical URL paths. Validation rejects dot/traversal components, empty or duplicate separators, percent encodings, backslashes, Unicode control/format characters, trailing dot/space components, Windows reserved names, excessive length, and collisions under `NFC(path).casefold()`.

The runtime proof type and seal are closure-private. A proof can only be obtained by verifying:

1. the complete manifest digest equals a trusted manifest digest;
2. exact path, length, and SHA-256 parity for every cached body;
3. exactly Form, Hub, and contracts;
4. every component names the same release, contract, and trusted manifest digest.

A proof from another manifest cannot authorize event creation even if `release_id` is reused.

## 7. Executable verification

Focused suite:

`python3 -m unittest discover -s tests/v2_contract -p 'test_*.py' -v`

The synthetic tests cover all preserved findings plus event identity, strict envelopes, cache integrity, state wording, DQ, concurrency at first open, and process termination before/after each implemented durable transaction boundary.

## 8. BLOCKED — DECISION

No implementation may infer or settle these dependencies:

1. **BLOCKED — DECISION:** institutional system owner, data controller, approver, and operational administrator.
2. **BLOCKED — DECISION:** production Firebase/GCP ownership, billing, authoritative Rules, indexes, environments, and backup capability.
3. **BLOCKED — DECISION:** production ingestion, device storage, analytics runtimes, service identities, and trusted manifest root.
4. **BLOCKED — DECISION:** storage, retention, conflict evidence, compaction, backup, restore, disaster recovery, and incident policies.
5. **BLOCKED — DECISION:** UUIDv7, stream-allocation, canonical-byte, clock, and entropy policy.
6. **BLOCKED — DECISION:** supported envelope/client/release compatibility matrix and migration/cutover authority.
7. **BLOCKED — DECISION:** duplicate-fingerprint fields, normalization, privacy controls, and DQ ownership.
8. **BLOCKED — DECISION:** stale/gapped/forked-event resolution authority beyond safe rejection.
9. **BLOCKED — DECISION:** reconciliation authority, cadence, tolerances, and clean-with-history definition.
10. **BLOCKED — DECISION:** resource limits for field and production operation.
11. **BLOCKED — DECISION:** cache fallback, atomic activation, paired rollback, staging domain, and rollout criteria.
12. **BLOCKED — DECISION:** Nepal HMIS/DHIS2 metadata and acceptance owner; OCHA format/delivery/acceptance owner; FHIR requirements.
13. **BLOCKED — DECISION:** identity/role model, post-trial classification/publication, indicator definitions, and approval authority.

## Completion boundary

Passing tests proves an executable immutable-authority review artifact only. It does not prove IndexedDB behavior, production authentication/authorization, production limits, monitoring, analytics, migration, backup/restore, institutional acceptance, or deployment safety. The maximum classification is **DONE — REVIEW ARTIFACT**.