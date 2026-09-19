#!/usr/bin/env python3
"""Transactional outbox, acknowledgement, clear, and crash contracts."""

from __future__ import annotations

import hashlib
import json
import os
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
SYNC_CLIENT = ROOT / "packages" / "sync-client"
sys.path[:0] = [str(CONTRACTS), str(SYNC_CLIENT)]

from mhpss_v2 import canonical_bytes, new_submission, uuid7  # noqa: E402
from release_contract import verify_runtime_components  # noqa: E402
from outbox import (  # noqa: E402
    ACKNOWLEDGED,
    CONFLICT,
    PENDING,
    AcknowledgementError,
    ClearBlocked,
    OutboxStore,
)

RUNTIME_PROOF = verify_runtime_components(
    {
        name: {"release_id": "test-release-a", "contract_version": "mhpss.event/1.0"}
        for name in ("form", "hub", "contracts")
    }
)


def envelope_bytes(index: int = 1) -> bytes:
    return canonical_bytes(
        new_submission(
            schema_name="synthetic.activity",
            payload={"count": index, "label": "synthetic"},
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/1",
            release_id="test-release-a",
            runtime_proof=RUNTIME_PROOF,
            event_id=uuid7(now_ms=1_800_000_000_000, random_bits=index),
        )
    )


def acknowledgement(body: bytes) -> dict[str, object]:
    event_id = json.loads(body)["event_id"]
    return {
        "ack_version": "mhpss.ack/1.0",
        "status": "accepted",
        "event_id": event_id,
        "accepted_body_sha256": hashlib.sha256(body).hexdigest(),
        "accepted_body_bytes": len(body),
        "canonical_sequence": 1,
        "contract_version": "mhpss.event/1.0",
    }


class TransactionalOutboxTests(unittest.TestCase):
    def test_concurrent_first_open_waits_instead_of_failing_locked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "client.sqlite3"
            barrier = threading.Barrier(12)

            def open_store(_: int) -> str:
                barrier.wait()
                return OutboxStore(database).integrity_check()

            with ThreadPoolExecutor(max_workers=12) as executor:
                results = list(executor.map(open_store, range(12)))
            self.assertEqual(results, ["ok"] * 12)

    def test_save_commits_source_and_exact_outbox_body_together(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = OutboxStore(Path(temporary_directory) / "client.sqlite3")
            body = envelope_bytes()
            event_id = store.save(body)

            self.assertEqual(store.source_body(event_id), body)
            self.assertEqual(store.outbox_item(event_id)["body"], body)
            self.assertEqual(store.outbox_item(event_id)["state"], PENDING)
            self.assertEqual(store.status(event_id)["user_state"], "saved_on_device_and_queued")
            self.assertEqual(store.integrity_check(), "ok")

    def test_crash_before_commit_leaves_neither_source_nor_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database = root / "client.sqlite3"
            body_path = root / "body.json"
            body_path.write_bytes(envelope_bytes())
            completed = self._crash_save(database, body_path, "before_commit")
            self.assertEqual(completed.returncode, 91)

            reopened = OutboxStore(database)
            self.assertEqual(reopened.counts(), {"sources": 0, "outbox": 0, "receipts": 0})
            self.assertEqual(reopened.integrity_check(), "ok")

    def test_crash_after_commit_leaves_source_and_queue_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            database = root / "client.sqlite3"
            body_path = root / "body.json"
            body = envelope_bytes()
            body_path.write_bytes(body)
            completed = self._crash_save(database, body_path, "after_commit")
            self.assertEqual(completed.returncode, 92)

            reopened = OutboxStore(database)
            event_id = json.loads(body)["event_id"]
            self.assertEqual(reopened.source_body(event_id), body)
            self.assertEqual(reopened.outbox_item(event_id)["state"], PENDING)
            self.assertEqual(reopened.save(body), event_id)
            self.assertEqual(reopened.counts(), {"sources": 1, "outbox": 1, "receipts": 0})

    def test_exact_read_back_acknowledgement_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = OutboxStore(Path(temporary_directory) / "client.sqlite3")
            body = envelope_bytes()
            event_id = store.save(body)
            valid = acknowledgement(body)
            invalid_cases = (
                {**valid, "event_id": uuid7(now_ms=1_800_000_000_000, random_bits=99)},
                {**valid, "accepted_body_sha256": "0" * 64},
                {**valid, "accepted_body_bytes": len(body) - 1},
                {key: value for key, value in valid.items() if key != "canonical_sequence"},
            )
            for invalid in invalid_cases:
                with self.subTest(invalid=invalid):
                    with self.assertRaises(AcknowledgementError):
                        store.acknowledge(event_id, invalid, read_back_body=body)
                    self.assertEqual(store.outbox_item(event_id)["state"], CONFLICT)
                    self.assertGreaterEqual(store.conflict_count(event_id), 1)
                    store.reset_conflict_for_retry(event_id)

            with self.assertRaises(AcknowledgementError):
                store.acknowledge(event_id, valid, read_back_body=None)
            self.assertEqual(store.outbox_item(event_id)["state"], CONFLICT)
            store.reset_conflict_for_retry(event_id)
            with self.assertRaises(AcknowledgementError):
                store.acknowledge(event_id, valid, read_back_body=body + b" ")
            self.assertEqual(store.outbox_item(event_id)["state"], CONFLICT)
            store.reset_conflict_for_retry(event_id)

            store.acknowledge(event_id, valid, read_back_body=body)
            self.assertEqual(store.outbox_item(event_id)["state"], ACKNOWLEDGED)
            self.assertEqual(store.status(event_id)["user_state"], "server_acknowledged")
            self.assertEqual(store.receipt(event_id)["body_sha256"], hashlib.sha256(body).hexdigest())

            changed = {**valid, "canonical_sequence": 999}
            with self.assertRaises(AcknowledgementError):
                store.acknowledge(event_id, changed, read_back_body=body)
            self.assertEqual(store.receipt(event_id)["canonical_sequence"], 1)
            self.assertEqual(store.outbox_item(event_id)["state"], CONFLICT)

    def test_clear_is_refused_when_any_obligation_is_not_acknowledged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = OutboxStore(Path(temporary_directory) / "client.sqlite3")
            first = envelope_bytes(1)
            second = envelope_bytes(2)
            first_id = store.save(first)
            second_id = store.save(second)
            store.acknowledge(first_id, acknowledgement(first), read_back_body=first)

            with self.assertRaises(ClearBlocked):
                store.clear_verified_payloads()
            self.assertEqual(store.source_body(first_id), first)
            self.assertEqual(store.source_body(second_id), second)

            store.acknowledge(second_id, acknowledgement(second), read_back_body=second)
            cleared = store.clear_verified_payloads()
            self.assertEqual(cleared, 2)
            self.assertIsNone(store.source_body(first_id))
            self.assertIsNone(store.outbox_item(first_id)["body"])
            self.assertIsNotNone(store.receipt(first_id))
            self.assertEqual(store.status(first_id)["user_state"], "server_acknowledged")

    def test_bounded_compaction_removes_only_oldest_acknowledged_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = OutboxStore(Path(temporary_directory) / "client.sqlite3")
            ids: list[str] = []
            for index in range(1, 4):
                body = envelope_bytes(index)
                event_id = store.save(body)
                store.acknowledge(event_id, acknowledgement(body), read_back_body=body)
                ids.append(event_id)
            pending_body = envelope_bytes(4)
            pending_id = store.save(pending_body)

            compacted = store.compact_acknowledged(max_payload_rows=1, max_payload_bytes=10_000)
            self.assertEqual(compacted, 2)
            self.assertIsNone(store.outbox_item(ids[0])["body"])
            self.assertIsNone(store.outbox_item(ids[1])["body"])
            self.assertIsNotNone(store.outbox_item(ids[2])["body"])
            self.assertEqual(store.outbox_item(pending_id)["body"], pending_body)
            self.assertEqual(store.compact_acknowledged(max_payload_rows=1, max_payload_bytes=10_000), 0)

    def test_retry_after_verified_clear_does_not_resurrect_payload_or_requeue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = OutboxStore(Path(temporary_directory) / "client.sqlite3")
            body = envelope_bytes()
            event_id = store.save(body)
            store.acknowledge(event_id, acknowledgement(body), read_back_body=body)
            store.clear_verified_payloads()

            self.assertEqual(store.save(body), event_id)
            self.assertIsNone(store.source_body(event_id))
            self.assertIsNone(store.outbox_item(event_id)["body"])
            self.assertEqual(store.outbox_item(event_id)["state"], ACKNOWLEDGED)

    def test_source_outbox_divergence_fails_closed_before_retry_or_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "client.sqlite3"
            store = OutboxStore(database)
            body = envelope_bytes()
            event_id = store.save(body)
            with sqlite3.connect(database) as connection:
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.execute("DELETE FROM outbox WHERE event_id = ?", (event_id,))

            with self.assertRaisesRegex(Exception, "invariant"):
                store.save(body)
            self.assertEqual(store.status(event_id)["user_state"], "conflict_recovery_required")
            with self.assertRaisesRegex(ClearBlocked, "invariant"):
                store.clear_verified_payloads()
            self.assertEqual(store.source_body(event_id), body)

    def test_corrupt_terminal_evidence_cannot_authorize_clear_or_compaction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "client.sqlite3"
            store = OutboxStore(database)
            body = envelope_bytes()
            event_id = store.save(body)
            store.acknowledge(event_id, acknowledgement(body), read_back_body=body)
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE receipts SET body_sha256 = ?, body_bytes = 0 WHERE event_id = ?",
                    ("0" * 64, event_id),
                )

            self.assertEqual(store.status(event_id)["user_state"], "conflict_recovery_required")
            with self.assertRaisesRegex(Exception, "terminal evidence"):
                store.save(body)
            with self.assertRaisesRegex(ClearBlocked, "terminal evidence"):
                store.clear_verified_payloads()
            with self.assertRaisesRegex(Exception, "terminal evidence"):
                store.compact_acknowledged(max_payload_rows=0, max_payload_bytes=0)
            self.assertEqual(store.source_body(event_id), body)
            self.assertEqual(store.outbox_item(event_id)["body"], body)

    def test_tampered_acknowledged_payload_cannot_be_compacted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "client.sqlite3"
            store = OutboxStore(database)
            body = envelope_bytes()
            event_id = store.save(body)
            store.acknowledge(event_id, acknowledgement(body), read_back_body=body)
            with sqlite3.connect(database) as connection:
                connection.execute("UPDATE outbox SET body = ? WHERE event_id = ?", (b"evil", event_id))

            self.assertEqual(store.status(event_id)["user_state"], "conflict_recovery_required")
            with self.assertRaisesRegex(Exception, "terminal evidence"):
                store.compact_acknowledged(max_payload_rows=0, max_payload_bytes=0)
            self.assertEqual(store.source_body(event_id), body)
            self.assertEqual(store.outbox_item(event_id)["body"], b"evil")

    def test_same_identity_different_body_is_durable_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = OutboxStore(Path(temporary_directory) / "client.sqlite3")
            first = envelope_bytes()
            event = json.loads(first)
            event["payload"] = {"different": True}
            second = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
            event_id = store.save(first)

            with self.assertRaisesRegex(Exception, "different immutable bytes"):
                store.save(second)
            self.assertEqual(store.outbox_item(event_id)["state"], CONFLICT)
            self.assertEqual(store.conflict_count(event_id), 1)
            self.assertEqual(store.latest_conflict_body(event_id), second)
            self.assertEqual(store.source_body(event_id), first)

    @staticmethod
    def _crash_save(database: Path, body_path: Path, failpoint: str) -> subprocess.CompletedProcess[str]:
        program = (
            "import sys; "
            f"sys.path[:0] = [{str(CONTRACTS)!r}, {str(SYNC_CLIENT)!r}]; "
            "from outbox import OutboxStore; "
            f"OutboxStore({str(database)!r}).save(open({str(body_path)!r}, 'rb').read(), crash_at={failpoint!r})"
        )
        return subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
