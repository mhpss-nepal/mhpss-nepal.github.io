# MHPSS Nepal V2 immutable-authority evidence ledger

Status: **DONE — REVIEW ARTIFACT candidate**

Executor: ☁️ Thar Lay/server, Kanban task `t_b62d39df`

Source: held local review artifact at exact base `9347d82197c4117f41e98ecbe971a60538fbeda4`

Workspace/output: `/root/mhpss-nepal-work/v2-authority-redesign`, branch `architecture/v2-immutable-authority`

Synchronization: server worktree only; not pushed, merged, deployed, or synchronized to Luna/Mac

Production: frozen; protected refs and deployments are verification-only

Data: local synthetic fixtures only

## Architectural rationale

The held artifact split authority across mutable payload, source, outbox, receipt, acknowledgement, and projection rows. It could therefore report success or permit deletion after one mutable copy changed. The redesign establishes a byte-rehashed append-only commit/event log in each trust domain. Payloads and projection caches are materializations; every state, acknowledgement, lineage, clear, compaction, and reconciliation decision is replayed from rehashed authority.

Conflict is represented as an immutable authority event and remains sticky until an explicit recovery event records actor, reason, and the exact conflict hash. Event identity is allocated only inside the trusted creation boundary. Runtime proof is closure-private and binds exact verified assets/components to a trusted manifest digest.

## Strict TDD evidence

The redesign regressions were added before implementation and observed failing for the expected missing behavior:

- `test_authority_redesign.py`: runtime verification rejected new manifest arguments; unsafe paths/collisions were accepted; public API exposed caller-selected identity.
- `test_device_authority.py`: legacy tables lacked hash-chained authority; corrupt pending bytes still emitted the alternate queued state; conflict could be acknowledged; no audited recovery/compaction evidence or acknowledgement/clear failpoints existed.
- `test_canonical_authority.py`: canonical integrity error type and immutable authority did not exist; lineage trusted projection metadata; replay/reconciliation trusted mutable digests; duplicate receipts were order-dependent.

Each slice then passed before the next was integrated. No production code for these redesign behaviors preceded its failing test.

## Acceptance mapping

| # | Mandatory regression | Executable evidence | Result |
|---|---|---|---|
| 1 | Corrupt compacted terminal evidence blocks every clear | `test_corrupt_compacted_evidence_blocks_every_later_clear` | Pass |
| 2 | Conflict cannot become acknowledged without audited recovery | `test_conflict_is_sticky_until_explicit_audited_recovery` | Pass |
| 3 | `incoming_sha256` hashes exact retained incoming bytes | same conflict test compares retained bytes and SHA-256 | Pass |
| 4 | Pending/source/outbox corruption never reports `durable_queued` | `test_pending_payload_corruption_fails_closed_without_durable_claim` | Pass |
| 5 | Lineage derives from rehashed immutable events | `test_lineage_and_projection_are_derived_from_rehashed_immutable_events` | Pass |
| 6 | Replay revalidates canonical immutable state | `test_replay_revalidates_canonical_bytes_before_returning_acknowledgement` | Pass |
| 7 | Reconciliation detects mutation, miskeying, duplicates, forks, gaps | canonical-authority reconciliation/fork tests | Pass |
| 8 | Release proof cannot be constructed or reused | `test_public_submission_allocates_identity_and_proof_is_manifest_bound` | Pass |
| 9 | Release paths reject traversal, aliases, separators, controls, encodings, collisions | `test_release_paths_are_canonical_and_collision_free` | Pass |
| 10 | One state vocabulary | `test_state_vocabulary_is_complete_and_unique`; outbox imports these constants | Pass |
| 11 | Public API rejects caller-selected event identity | runtime/identity test asserts `TypeError` | Pass |
| 12 | Asymmetric clear cannot remove the last recovery copy | `test_asymmetric_missing_payload_and_malformed_ack_fail_closed` | Pass |
| 13 | Malformed terminal acknowledgement fails closed without crash | same asymmetric/malformed acknowledgement test | Pass |
| 14 | Compaction metadata rehashed, validated, bounded | `test_compaction_metadata_is_rehashed_validated_and_bounded` | Pass |
| 15 | Process termination at durable boundaries preserves recovery/idempotency | device and canonical process-termination tests | Pass |

## Checkpoints

| Time (Nepal, UTC+05:45) | Evidence | Result |
|---|---|---|
| 2026-09-19 20:16 | Parent task, independent review including full comment, held contracts, held evidence ledger, MHPSS context, offline-sync gate, and monorepo safety gate read before edits | Scope and constraints confirmed |
| 2026-09-19 20:16 | Exact baseline verified with `git rev-parse HEAD`, branch, status, and `git diff --check` | Base `9347d82197c4117f41e98ecbe971a60538fbeda4`; branch `architecture/v2-immutable-authority`; initially clean |
| 2026-09-19 20:16 | New redesign tests run before implementation | Failed for missing immutable authority, opaque trusted proof, path rules, recovery audit, failpoints, and single-state vocabulary |
| 2026-09-19 20:16 | Focused redesign slices rerun after implementation | Passed |
| 2026-09-19 20:16 | `python3 -m unittest discover -s tests/v2_contract -p 'test_*.py' -q` | 58 tests passed |
| 2026-09-20 03:15 | Independent re-run on recovered worktree: `python3 -m unittest discover -s tests/v2_contract -t .` | 58 tests passed |
| 2026-09-20 03:15 | Independent re-run of monorepo gate: `PYTHONPATH=tests python3 -m unittest test_build test_validate test_adversarial test_third_review` | 27 tests passed, 1 skipped |
| 2026-09-20 03:15 | `git diff --check` on all 12 modified paths | Clean, no whitespace errors |
| 2026-09-20 03:15 | Production ref check `git rev-parse origin/main` | `68bf197abe56dd0265dca245e61809100b4c3901` (unchanged; production frozen) |

Recovery note: two prior automated attempts failed for environmental reasons, not code defects — attempt 1 exceeded the 21600s task limit, attempt 2 exhausted its 20-turn goal budget while the Codex provider returned HTTP 503/429 usage-limit errors and the goal judge returned InternalServerError. At recovery time no worker or dispatcher process was alive. The 15/15 regression findings above were re-derived from the preserved worktree and independently re-run rather than accepted from a stale claim.

Final full-suite, compile, security, independent review, commit, exact head, clean-worktree, and production-ref results are appended after those commands run.

## Implemented evidence

- `packages/contracts/mhpss_v2.py`: `mhpss.event/2.0`, trusted-boundary identity, manifest digest in each envelope.
- `packages/contracts/release_contract.py`: canonical cross-platform path policy, complete asset verification, closure-private trusted proof.
- `packages/contracts/sync_states.py`: one exported state vocabulary.
- `packages/sync-client/outbox.py`: hash-chained device authority, exact-byte recovery, sticky conflict, audited recovery, bounded compaction, fail-closed status/clear, durable failpoints.
- `services/ingest/ingest.py`: exact-byte canonical authority, replay-derived acknowledgement, immutable lineage/projection/DQ/reconciliation, canonical failpoints.
- `tests/v2_contract/`: preserved and new synthetic regressions for all mandatory findings.
- `docs/V2-CONTRACTS.md`: redesigned contract, rationale, interface, authority boundaries, and blocked decisions.

## Scope verification

- No `apps/` file was edited.
- No browser direct canonical write or V1/V2 dual-write was added.
- No network, Firebase/Firestore, credential, deployment, PR, merge, or push operation was added.
- No institutional owner, Rules, retention, runtime, limit, HMIS/DHIS2, OCHA, or FHIR decision was invented.
- This remains a local-only review artifact. Integration, merge, deployment, and production readiness remain closed pending independent review and institutional decisions.

## BLOCKED — DECISION

Institutional ownership/data-controller roles; production cloud ownership/Rules/indexes/billing; storage and ingestion runtimes; retention/compaction/backup/restore/incident policy; identity and canonical-byte policy; migration/cutover; DQ and reconciliation authority; production limits; trusted manifest root/cache activation/rollback; Nepal HMIS/DHIS2/OCHA/FHIR mappings and acceptance owners; roles/classification/publication/indicator approval.