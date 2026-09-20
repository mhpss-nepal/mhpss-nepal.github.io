#!/usr/bin/env python3
"""Canonical immutable-authority, lineage, replay, and reconciliation regressions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts"
INGEST = ROOT / "services" / "ingest"
sys.path[:0] = [str(CONTRACTS), str(INGEST), str(Path(__file__).parent)]

from ingest import IngestIntegrityError, IngestStore  # noqa: E402
from mhpss_v2 import canonical_bytes, new_correction, new_submission  # noqa: E402
from test_authority_redesign import verified_runtime  # noqa: E402


def submission(index: int) -> dict[str, object]:
    manifest, proof = verified_runtime()
    return new_submission(
        schema_name="synthetic.activity",
        payload={"count": index, "label": f"synthetic-{index}"},
        duplicate_fingerprint=None,
        occurred_at="2026-09-19T00:00:00Z",
        client_version="test-client/2",
        release_id=manifest.release_id,
        runtime_proof=proof,
    )


def correction(predecessor: dict[str, object], count: int) -> dict[str, object]:
    manifest, proof = verified_runtime()
    return new_correction(
        predecessor=predecessor,
        payload={"count": count, "label": f"corrected-{count}"},
        duplicate_fingerprint=None,
        occurred_at=f"2026-09-19T00:0{count}:00Z",
        client_version="test-client/2",
        release_id=manifest.release_id,
        runtime_proof=proof,
    )


def receipt(result: dict[str, object]) -> dict[str, str]:
    acknowledgement = result["acknowledgement"]
    assert isinstance(acknowledgement, dict)
    return {
        "event_id": str(acknowledgement["event_id"]),
        "body_sha256": str(acknowledgement["accepted_body_sha256"]),
    }


class CanonicalAuthorityTests(unittest.TestCase):
    def test_lineage_and_projection_are_derived_from_rehashed_immutable_events(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "canonical.sqlite3"
            store = IngestStore(database)
            first = submission(1)
            second = correction(first, 2)
            store.ingest(canonical_bytes(first))
            store.ingest(canonical_bytes(second))

            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE projection_cache SET event_id = ?, revision = 99, body_sha256 = ? WHERE stream_id = ?",
                    (first["event_id"], "0" * 64, first["stream_id"]),
                )
            third = correction(second, 3)
            result = store.ingest(canonical_bytes(third))

            self.assertEqual(result["outcome"], "accepted")
            self.assertEqual(
                store.lineage(first["stream_id"]),
                [third["event_id"], second["event_id"], first["event_id"]],
            )
            self.assertEqual(store.projection(first["stream_id"])["event_id"], third["event_id"])

    def test_replay_revalidates_canonical_bytes_before_returning_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "canonical.sqlite3"
            store = IngestStore(database)
            body = canonical_bytes(submission(4))
            accepted = store.ingest(body)
            self.assertEqual(store.ingest(body)["acknowledgement"], accepted["acknowledgement"])

            with sqlite3.connect(database) as connection:
                row = connection.execute(
                    "SELECT data FROM authority_records WHERE kind = 'canonical_event'"
                ).fetchone()
                changed = json.loads(row[0])
                changed["body_sha256"] = "0" * 64
                connection.execute(
                    "UPDATE authority_records SET data = ? WHERE kind = 'canonical_event'",
                    (json.dumps(changed, separators=(",", ":"), sort_keys=True).encode(),),
                )
            with self.assertRaises(IngestIntegrityError):
                store.ingest(body)

    def test_reconciliation_detects_body_mutation_and_unrelated_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "canonical.sqlite3"
            store = IngestStore(database)
            first = submission(5)
            second = correction(first, 6)
            results = [store.ingest(canonical_bytes(event)) for event in (first, second)]
            receipts = [receipt(result) for result in results]
            self.assertTrue(store.reconcile(client_receipts=receipts)["clean"])

            with sqlite3.connect(database) as connection:
                connection.execute(
                    "INSERT INTO projection_cache VALUES (?, ?, ?, ?)",
                    ("unrelated-stream", first["event_id"], 1, hashlib.sha256(canonical_bytes(first)).hexdigest()),
                )
            report = store.reconcile(client_receipts=receipts)
            self.assertFalse(report["clean"])
            self.assertIn("UNRELATED_PROJECTION", {item["code"] for item in report["differences"]})

            with sqlite3.connect(database) as connection:
                row = connection.execute(
                    "SELECT data FROM authority_records WHERE kind = 'canonical_event' ORDER BY sequence LIMIT 1"
                ).fetchone()
                changed = json.loads(row[0])
                changed["body_b64"] = "ZXZpbA=="
                connection.execute(
                    "UPDATE authority_records SET data = ? WHERE kind = 'canonical_event' AND sequence = 1",
                    (json.dumps(changed, separators=(",", ":"), sort_keys=True).encode(),),
                )
            corrupted = store.reconcile(client_receipts=receipts)
            self.assertFalse(corrupted["clean"])
            self.assertIn("AUTHORITY_INTEGRITY_FAILURE", {item["code"] for item in corrupted["differences"]})

    def test_duplicate_receipts_are_order_independent_and_forks_or_gaps_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "canonical.sqlite3"
            store = IngestStore(database)
            first = submission(7)
            second = correction(first, 8)
            results = [store.ingest(canonical_bytes(event)) for event in (first, second)]
            receipts = [receipt(result) for result in results]
            forward = store.reconcile(client_receipts=receipts + [receipts[0]])
            reverse = store.reconcile(client_receipts=list(reversed(receipts + [receipts[0]])))
            self.assertFalse(forward["clean"])
            self.assertEqual(forward["differences"], reverse["differences"])
            self.assertEqual(forward["evidence_sha256"], reverse["evidence_sha256"])

            fork = correction(first, 9)
            with sqlite3.connect(database) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("BEGIN IMMEDIATE")
                IngestStore._append_record(
                    connection,
                    "canonical_event",
                    fork["event_id"],
                    IngestStore._event_value(canonical_bytes(fork)),
                )
                connection.commit()
            forked = store.reconcile(client_receipts=receipts)
            self.assertFalse(forked["clean"])
            self.assertIn("AUTHORITY_INTEGRITY_FAILURE", {item["code"] for item in forked["differences"]})

    def test_process_termination_at_canonical_commit_boundaries_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            body = canonical_bytes(submission(10))
            body_path = root / "body.json"
            body_path.write_bytes(body)
            for failpoint, code, expected_events in (
                ("before_commit", 97, 0),
                ("after_commit", 98, 1),
            ):
                with self.subTest(failpoint=failpoint):
                    database = root / f"{failpoint}.sqlite3"
                    completed = self._crash_ingest(database, body_path, failpoint)
                    self.assertEqual(completed.returncode, code, completed.stderr)
                    reopened = IngestStore(database)
                    self.assertEqual(reopened.counts()["events"], expected_events)
                    result = reopened.ingest(body)
                    self.assertIn(result["outcome"], {"accepted", "replayed"})
                    self.assertEqual(reopened.counts()["events"], 1)

    @staticmethod
    def _crash_ingest(
        database: Path, body_path: Path, failpoint: str
    ) -> subprocess.CompletedProcess[str]:
        program = (
            "import sys; "
            f"sys.path[:0] = [{str(CONTRACTS)!r}, {str(INGEST)!r}]; "
            "from ingest import IngestStore; "
            f"IngestStore({str(database)!r}).ingest(open({str(body_path)!r}, 'rb').read(), crash_at={failpoint!r})"
        )
        return subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
