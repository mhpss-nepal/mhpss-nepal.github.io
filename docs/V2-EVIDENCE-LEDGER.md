# MHPSS Nepal V2 contract evidence ledger

Implementation checkpoint: **DONE — REVIEW ARTIFACT candidate**

Independent verdict: **HELD — REDESIGN REQUIRED**

Executor: ☁️ Thar Lay/server, Kanban task `t_147077e8`

Workspace: `/root/mhpss-nepal-work/v2-contracts`

Branch: `architecture/v2-contracts`

Base: `b1f32cb2ab3f5341b13f7f93b1bb46decab57b6e`

Production: frozen and unchanged

Data: synthetic fixtures only

## Checkpoints

| Time (Nepal, UTC+05:45) | Evidence | Result |
|---|---|---|
| 2026-09-19 18:20 | Required brief, approved roadmap, pending decisions, and independent review gate read before implementation | Scope and hard boundaries confirmed |
| 2026-09-19 18:20 | Strict TDD slices run individually for event identity, outbox/crash behavior, ingestion/projection/DQ/reconciliation, cache/release, and sync wording | Each slice observed failing for missing behavior before implementation and passing after implementation |
| 2026-09-19 18:20 | `python3 -m unittest discover -s tests/v2_contract -p 'test_*.py' -v` | 31 tests passed at first integrated V2 checkpoint |
| 2026-09-19 18:20 | Two independent adversarial code reviews | Failed closed with reconciliation, outbox-evidence, conflict-state, malformed-input, manifest, mixed-version, schema-lineage, and concurrent-open findings; one consolidated test-first correction applied |
| 2026-09-19 18:20 | Final `python3 -m unittest discover -s tests/v2_contract -p 'test_*.py' -v` after correction | 44 V2 contract tests passed |
| 2026-09-19 18:20 | Final `python3 -m unittest discover -s tests -v` after correction | 71 tests passed; 1 pre-existing Playwright-dependent test skipped because Playwright is unavailable |
| 2026-09-19 18:20 | Two independent adversarial re-reviews after correction | Failed closed again on equivalent integrity boundaries; local patching stopped under the two-cycle ceiling and the candidate was held for redesign |
| 2026-09-19 18:20 | `python3 -m compileall -q packages services tests/v2_contract` | Passed |
| 2026-09-19 18:20 | `git diff --check` | Passed |
| 2026-09-19 18:20 | Network/production-write scan of new `packages/` and `services/` | No network endpoint, Firebase/Firestore call, deployment, credential, or production integration found; only explicit non-production documentation wording matched |

## Implemented evidence

- `packages/contracts/mhpss_v2.py`: strict versioned envelope, UUIDv7 event identity, canonical bytes, corrections/voids, legacy provenance.
- `packages/contracts/sync_states.py`: explicit evidence-gated sync states and truthful user wording.
- `packages/contracts/release_contract.py`: deeply immutable paired release manifest, content-digest verification, complete runtime proof, mixed-version rejection.
- `packages/sync-client/outbox.py`: SQLite reference for atomic source/outbox, immutable exact-body acknowledgement read-back, durable conflict recovery, terminal-evidence revalidation, fail-closed clear, bounded terminal compaction, crash failpoints.
- `services/ingest/ingest.py`: sole canonical reference writer, validation, idempotency, conflict evidence, schema-preserving monotonic projection, DQ queue/resolution, bidirectional snapshot reconciliation, crash failpoints.
- `tests/v2_contract/`: synthetic executable regression specifications covering known V1 identity, retry, stale-write, source/queue crash, clear, cache, and mixed-version failure classes.
- `docs/V2-CONTRACTS.md`: interface contract, invariants, error semantics, scope boundary, and all unresolved institutional dependencies marked `BLOCKED — DECISION`.

## Scope verification

- No production repository, ref, URL, database, Firebase/Firestore resource, credential, or deployment was changed.
- No browser direct canonical write path was added.
- No V1/V2 dual-write path was added.
- Existing V1 application files under `apps/` were not edited.
- No institutional owner, authoritative Rules, retention policy, runtime, HMIS/OCHA mapping, or production limit was invented.

## Preserved blocking findings after the two-cycle ceiling

These findings are reproducible and are not waived by the green committed suite:

1. **Outbox terminal integrity:** a compacted event with later-corrupted receipt evidence does not block clearing another event's payload.
2. **Conflict recovery:** a valid acknowledgement can move a conflicted obligation to acknowledged without an explicit recovery transition.
3. **Conflict evidence:** acknowledgement-mismatch `incoming_sha256` is not computed over the exact retained `incoming_body` bytes.
4. **Lineage authority:** corrupted projection metadata can authorize a forked successor instead of deriving lineage solely from immutable events.
5. **Canonical integrity:** reconciliation trusts stored event digests and can report clean after canonical event body bytes are changed.
6. **Projection integrity:** reconciliation can miss a projection keyed by an unrelated stream while pointing at an existing historical event.
7. **Acknowledgement replay:** an altered stored acknowledgement can be returned on exact-body replay without revalidation against immutable canonical state.
8. **Pending status:** pending source/outbox bytes are not revalidated before reporting `saved_on_device_and_queued`.
9. **Runtime proof:** `RuntimeProof` is directly constructible, so callers can bypass complete Form/Hub/contracts verification.
10. **Release paths:** the manifest accepts traversal/alias and control-character URL paths such as `/../secret`, `/a/../b`, `//double`, and newline-containing paths.

The next implementation must replace trust in mutable projection/receipt
metadata with one immutable commit-envelope authority, derive current state and
reconciliation from that authority, make conflict transitions sticky until an
audited recovery event, and make runtime/release proof unforgeable by API
construction. This is an architecture redesign, not another incremental patch.

## Review handoff

The parent task has a pre-created independent review child, `t_6d578ef8`. Parent completion releases that review lane with this held verdict and exact head. The child must independently confirm the evidence and keep integration, merge, and deployment closed. It cannot declare production readiness.

The final commit hash, exact changed-file list, final all-suite count, and clean-worktree verification are appended in the parent Kanban completion metadata after commit.
