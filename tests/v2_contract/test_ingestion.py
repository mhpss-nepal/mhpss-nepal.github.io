#!/usr/bin/env python3
"""Ingestion, immutable projection, DQ, and reconciliation contracts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts"
INGEST = ROOT / "services" / "ingest"
sys.path[:0] = [str(CONTRACTS), str(INGEST)]

from ingest import IngestStore  # noqa: E402
from mhpss_v2 import canonical_bytes, new_correction as _new_correction, new_submission as _new_submission, uuid7  # noqa: E402
from release_contract import ReleaseManifest, verify_runtime_components  # noqa: E402

_BODIES = {"/index.html": b"public", "/form/app.js": b"form", "/hub/app.js": b"hub"}
_MANIFEST = ReleaseManifest.from_bodies(
    release_id="test-release-a",
    contract_version="mhpss.event/2.0",
    cache_version="test-cache-a",
    bodies=_BODIES,
)
RUNTIME_PROOF = verify_runtime_components(
    manifest=_MANIFEST,
    cached_bodies=_BODIES,
    components={
        name: {
            "release_id": "test-release-a",
            "contract_version": "mhpss.event/2.0",
            "manifest_sha256": _MANIFEST.digest(),
        }
        for name in ("form", "hub", "contracts")
    },
    trusted_manifest_sha256=_MANIFEST.digest(),
)


def new_submission(**values):
    values.pop("event_id", None)
    return _new_submission(**values)


def new_correction(**values):
    values.pop("event_id", None)
    return _new_correction(**values)


def submission(index: int, *, fingerprint: str | None = None) -> dict[str, object]:
    return new_submission(
        schema_name="synthetic.activity",
        payload={"count": index, "label": f"synthetic-{index}"},
        duplicate_fingerprint=fingerprint,
        occurred_at="2026-09-19T00:00:00Z",
        client_version="test-client/1",
        release_id="test-release-a",
        runtime_proof=RUNTIME_PROOF,
        event_id=uuid7(now_ms=1_800_000_000_000, random_bits=index),
    )


class IngestionTests(unittest.TestCase):
    def test_concurrent_first_open_waits_instead_of_failing_locked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "canonical.sqlite3"
            barrier = threading.Barrier(12)

            def open_store(_: int) -> str:
                barrier.wait()
                return IngestStore(database).integrity_check()

            with ThreadPoolExecutor(max_workers=12) as executor:
                results = list(executor.map(open_store, range(12)))
            self.assertEqual(results, ["ok"] * 12)

    def test_retry_is_idempotent_and_returns_the_committed_exact_body_ack(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            body = canonical_bytes(submission(1))
            accepted = store.ingest(body)
            replayed = store.ingest(body)

            self.assertEqual(accepted["outcome"], "accepted")
            self.assertEqual(replayed["outcome"], "replayed")
            self.assertEqual(accepted["acknowledgement"], replayed["acknowledgement"])
            self.assertEqual(accepted["acknowledgement"]["accepted_body_sha256"], hashlib.sha256(body).hexdigest())
            self.assertEqual(store.counts()["events"], 1)
            self.assertEqual(store.event_body(json.loads(body)["event_id"]), body)

    def test_same_event_id_with_different_body_is_a_durable_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            first = submission(2)
            second = {**first, "payload": {"count": 999, "label": "different"}}
            first_body = canonical_bytes(first)
            second_body = canonical_bytes(second)

            self.assertEqual(store.ingest(first_body)["outcome"], "accepted")
            result = store.ingest(second_body)

            self.assertEqual(result["outcome"], "conflict")
            self.assertEqual(result["error"]["code"], "EVENT_ID_BODY_CONFLICT")
            self.assertEqual(store.event_body(first["event_id"]), first_body)
            self.assertEqual(store.counts()["events"], 1)
            self.assertEqual(store.counts()["conflicts"], 1)
            reopened = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            self.assertEqual(reopened.counts()["conflicts"], 1)

    def test_ordered_correction_advances_projection_without_mutating_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            first = submission(3)
            second = new_correction(
                predecessor=first,
                payload={"count": 4, "label": "corrected"},
                duplicate_fingerprint=None,
                occurred_at="2026-09-19T00:01:00Z",
                client_version="test-client/1",
                release_id="test-release-a",
                runtime_proof=RUNTIME_PROOF,
                event_id=uuid7(now_ms=1_800_000_000_001, random_bits=30),
            )
            first_body = canonical_bytes(first)
            second_body = canonical_bytes(second)
            store.ingest(first_body)
            result = store.ingest(second_body)

            self.assertEqual(result["outcome"], "accepted")
            self.assertEqual(store.event_body(first["event_id"]), first_body)
            self.assertEqual(store.projection(first["stream_id"])["event_id"], second["event_id"])
            self.assertEqual(store.projection(first["stream_id"])["revision"], 2)
            self.assertEqual(store.lineage(first["stream_id"]), [second["event_id"], first["event_id"]])

    def test_stale_or_out_of_order_correction_cannot_roll_back_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            first = submission(4)
            second = new_correction(
                predecessor=first,
                payload={"count": 2},
                duplicate_fingerprint=None,
                occurred_at="2026-09-19T00:01:00Z",
                client_version="test-client/1",
                release_id="test-release-a",
                runtime_proof=RUNTIME_PROOF,
                event_id=uuid7(now_ms=1_800_000_000_001, random_bits=40),
            )
            stale = new_correction(
                predecessor=first,
                payload={"count": 3},
                duplicate_fingerprint=None,
                occurred_at="2026-09-19T00:02:00Z",
                client_version="test-client/1",
                release_id="test-release-a",
                runtime_proof=RUNTIME_PROOF,
                event_id=uuid7(now_ms=1_800_000_000_002, random_bits=41),
            )
            store.ingest(canonical_bytes(first))
            store.ingest(canonical_bytes(second))
            result = store.ingest(canonical_bytes(stale))

            self.assertEqual(result["outcome"], "rejected")
            self.assertEqual(result["error"]["code"], "STALE_OR_GAPPED_REVISION")
            self.assertEqual(store.projection(first["stream_id"])["event_id"], second["event_id"])
            self.assertEqual(store.counts()["events"], 2)

    def test_correction_cannot_change_schema_within_a_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            first = submission(42)
            correction = new_correction(
                predecessor=first,
                payload={"count": 2},
                duplicate_fingerprint=None,
                occurred_at="2026-09-19T00:01:00Z",
                client_version="test-client/1",
                release_id="test-release-a",
                runtime_proof=RUNTIME_PROOF,
                event_id=uuid7(now_ms=1_800_000_000_001, random_bits=42),
            )
            correction["schema_name"] = "unrelated.schema"
            store.ingest(canonical_bytes(first))
            result = store.ingest(canonical_bytes(correction))
            self.assertEqual(result["outcome"], "rejected")
            self.assertEqual(result["error"]["code"], "STALE_OR_GAPPED_REVISION")
            self.assertEqual(store.projection(first["stream_id"])["event_id"], first["event_id"])

    def test_malformed_or_unsupported_envelope_leaves_predecessor_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            first = submission(5)
            store.ingest(canonical_bytes(first))
            malformed = b'{"contract_version":"mhpss.event/1.0","contract_version":"bad"}'
            result = store.ingest(malformed)

            self.assertEqual(result["outcome"], "rejected")
            self.assertEqual(result["error"]["code"], "INVALID_ENVELOPE")
            self.assertEqual(store.projection(first["stream_id"])["event_id"], first["event_id"])
            self.assertEqual(store.counts()["events"], 1)

    def test_duplicate_fingerprint_opens_dq_work_but_never_controls_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            first = canonical_bytes(submission(6, fingerprint="sha256:duplicate-candidate"))
            second = canonical_bytes(submission(7, fingerprint="sha256:duplicate-candidate"))
            store.ingest(first)
            store.ingest(second)
            store.ingest(second)

            self.assertEqual(store.counts()["events"], 2)
            self.assertEqual(store.counts()["projections"], 2)
            self.assertEqual(store.counts()["dq_items"], 1)
            item = store.dq_items()[0]
            self.assertEqual(item["rule_code"], "POSSIBLE_DUPLICATE")
            self.assertEqual(item["status"], "open")

    def test_correction_with_same_fingerprint_does_not_duplicate_its_own_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            first = submission(50, fingerprint="sha256:same-stream")
            correction = new_correction(
                predecessor=first,
                payload={"count": 51},
                duplicate_fingerprint="sha256:same-stream",
                occurred_at="2026-09-19T00:01:00Z",
                client_version="test-client/1",
                release_id="test-release-a",
                runtime_proof=RUNTIME_PROOF,
                event_id=uuid7(now_ms=1_800_000_000_001, random_bits=50),
            )
            store.ingest(canonical_bytes(first))
            store.ingest(canonical_bytes(correction))
            self.assertEqual(store.counts()["dq_items"], 0)

    def test_dq_resolution_requires_an_accepted_correction_and_retains_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "canonical.sqlite3"
            store = IngestStore(database)
            first = submission(60, fingerprint="sha256:duplicate-candidate")
            candidate = submission(61, fingerprint="sha256:duplicate-candidate")
            store.ingest(canonical_bytes(first))
            store.ingest(canonical_bytes(candidate))
            item = store.dq_items()[0]
            correction = new_correction(
                predecessor=candidate,
                payload={"count": 61, "label": "reviewed-correction"},
                duplicate_fingerprint=None,
                occurred_at="2026-09-19T00:03:00Z",
                client_version="test-client/1",
                release_id="test-release-a",
                runtime_proof=RUNTIME_PROOF,
                event_id=uuid7(now_ms=1_800_000_000_003, random_bits=62),
            )
            with self.assertRaisesRegex(ValueError, "accepted correction"):
                store.resolve_dq(item["dq_id"], correction["event_id"])

            store.ingest(canonical_bytes(correction))
            store.resolve_dq(item["dq_id"], correction["event_id"])
            resolved = store.dq_items()[0]
            self.assertEqual(resolved["status"], "resolved")
            self.assertEqual(resolved["resolved_by_event_id"], correction["event_id"])
            self.assertEqual(store.counts()["dq_items"], 1)
            reopened = IngestStore(database)
            self.assertEqual(reopened.dq_items()[0]["status"], "resolved")

    def test_crash_boundaries_are_atomic_and_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            body_path = root / "body.json"
            body = canonical_bytes(submission(8))
            body_path.write_bytes(body)
            for failpoint, returncode, expected in (
                ("before_commit", 97, 0),
                ("after_commit", 98, 1),
            ):
                with self.subTest(failpoint=failpoint):
                    database = root / f"{failpoint}.sqlite3"
                    completed = self._crash_ingest(database, body_path, failpoint)
                    self.assertEqual(completed.returncode, returncode)
                    reopened = IngestStore(database)
                    self.assertEqual(reopened.counts()["events"], expected)
                    retried = reopened.ingest(body)
                    self.assertIn(retried["outcome"], {"accepted", "replayed"})
                    self.assertEqual(reopened.counts()["events"], 1)
                    self.assertEqual(reopened.integrity_check(), "ok")

    def test_reconciliation_reports_machine_readable_divergence_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = IngestStore(Path(temporary_directory) / "canonical.sqlite3")
            body = canonical_bytes(submission(9))
            result = store.ingest(body)
            event_id = json.loads(body)["event_id"]
            clean = store.reconcile(
                client_receipts=[
                    {
                        "event_id": event_id,
                        "body_sha256": result["acknowledgement"]["accepted_body_sha256"],
                    }
                ]
            )
            self.assertTrue(clean["clean"])
            self.assertEqual(clean["differences"], [])

            divergent = store.reconcile(
                client_receipts=[{"event_id": event_id, "body_sha256": "0" * 64}]
            )
            self.assertFalse(divergent["clean"])
            self.assertEqual(divergent["differences"][0]["code"], "CLIENT_CANONICAL_DIGEST_MISMATCH")
            self.assertEqual(store.counts()["events"], 1)

    def test_reconciliation_requires_complete_unique_receipts_and_current_projections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "canonical.sqlite3"
            store = IngestStore(database)
            bodies = [canonical_bytes(submission(index)) for index in (70, 71)]
            results = [store.ingest(body) for body in bodies]
            receipts = [
                {
                    "event_id": json.loads(body)["event_id"],
                    "body_sha256": result["acknowledgement"]["accepted_body_sha256"],
                }
                for body, result in zip(bodies, results)
            ]
            for supplied, code in (
                ([], "CANONICAL_EVENT_MISSING_CLIENT_RECEIPT"),
                (receipts[:1], "CANONICAL_EVENT_MISSING_CLIENT_RECEIPT"),
                (receipts + [receipts[0]], "DUPLICATE_CLIENT_RECEIPT"),
            ):
                with self.subTest(code=code):
                    report = store.reconcile(client_receipts=supplied)
                    self.assertFalse(report["clean"])
                    self.assertIn(code, {item["code"] for item in report["differences"]})

            first_event = json.loads(bodies[0])
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE projection_cache SET revision = 99, body_sha256 = ? WHERE stream_id = ?",
                    ("0" * 64, first_event["stream_id"]),
                )
            report = store.reconcile(client_receipts=receipts)
            self.assertFalse(report["clean"])
            self.assertIn("STALE_OR_CORRUPT_PROJECTION", {item["code"] for item in report["differences"]})

    @staticmethod
    def _crash_ingest(database: Path, body_path: Path, failpoint: str) -> subprocess.CompletedProcess[str]:
        program = (
            "import sys; "
            f"sys.path[:0] = [{str(CONTRACTS)!r}, {str(INGEST)!r}]; "
            "from ingest import IngestStore; "
            f"IngestStore({str(database)!r}).ingest(open({str(body_path)!r}, 'rb').read(), crash_at={failpoint!r})"
        )
        return subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
