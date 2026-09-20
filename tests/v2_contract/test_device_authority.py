#!/usr/bin/env python3
"""Device authority, recovery, compaction, and crash regressions."""

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
SYNC_CLIENT = ROOT / "packages" / "sync-client"
sys.path[:0] = [str(CONTRACTS), str(SYNC_CLIENT), str(Path(__file__).parent)]

from mhpss_v2 import CONTRACT_VERSION, canonical_bytes, new_submission  # noqa: E402
from outbox import AcknowledgementError, ClearBlocked, OutboxError, OutboxStore  # noqa: E402
from sync_states import ACKNOWLEDGED, CONFLICT, CREATED, DURABLE_QUEUED  # noqa: E402
from test_authority_redesign import verified_runtime  # noqa: E402


def envelope_bytes(index: int) -> bytes:
    manifest, proof = verified_runtime()
    return canonical_bytes(
        new_submission(
            schema_name="synthetic.activity",
            payload={"count": index, "label": "synthetic"},
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/2",
            release_id=manifest.release_id,
            runtime_proof=proof,
        )
    )


def acknowledgement(body: bytes, sequence: int = 1) -> dict[str, object]:
    event_id = json.loads(body)["event_id"]
    return {
        "ack_version": "mhpss.ack/2.0",
        "status": "accepted",
        "event_id": event_id,
        "accepted_body_sha256": hashlib.sha256(body).hexdigest(),
        "accepted_body_bytes": len(body),
        "canonical_sequence": sequence,
        "contract_version": CONTRACT_VERSION,
    }


class DeviceAuthorityTests(unittest.TestCase):
    def test_pending_payload_corruption_fails_closed_without_durable_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "device.sqlite3"
            store = OutboxStore(database)
            body = envelope_bytes(1)
            event_id = store.save(body)
            self.assertEqual(store.status(event_id)["user_state"], DURABLE_QUEUED)

            with sqlite3.connect(database) as connection:
                connection.execute("UPDATE authority_payloads SET body = ? WHERE event_id = ?", (b"evil", event_id))

            self.assertEqual(store.status(event_id)["user_state"], CONFLICT)
            with self.assertRaises(OutboxError):
                store.pending_bodies()

    def test_conflict_is_sticky_until_explicit_audited_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = OutboxStore(Path(temporary_directory) / "device.sqlite3")
            body = envelope_bytes(2)
            event_id = store.save(body)
            invalid_ack = {**acknowledgement(body), "accepted_body_sha256": "0" * 64}
            incoming_bytes = json.dumps(
                invalid_ack, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8") + b"\n" + body

            with self.assertRaises(AcknowledgementError):
                store.acknowledge(event_id, invalid_ack, read_back_body=body)
            self.assertEqual(store.status(event_id)["user_state"], CONFLICT)
            self.assertEqual(store.latest_conflict_body(event_id), incoming_bytes)
            self.assertEqual(store.latest_conflict_digest(event_id), hashlib.sha256(incoming_bytes).hexdigest())

            with self.assertRaises(AcknowledgementError):
                store.acknowledge(event_id, acknowledgement(body), read_back_body=body)
            self.assertEqual(store.status(event_id)["user_state"], CONFLICT)

            recovery_hash = store.record_recovery(
                event_id,
                actor="synthetic-reviewer",
                reason="verified exact canonical read-back after mismatch",
            )
            self.assertEqual(len(recovery_hash), 64)
            store.acknowledge(event_id, acknowledgement(body), read_back_body=body)
            self.assertEqual(store.status(event_id)["user_state"], ACKNOWLEDGED)
            self.assertEqual(store.recovery_events(event_id)[0]["actor"], "synthetic-reviewer")

            changed_ack = {**acknowledgement(body), "canonical_sequence": 99}
            with self.assertRaises(AcknowledgementError):
                store.acknowledge(event_id, changed_ack, read_back_body=body)
            self.assertEqual(store.status(event_id)["user_state"], CONFLICT)
            store.record_recovery(
                event_id,
                actor="synthetic-reviewer",
                reason="revalidated the original immutable acknowledgement",
            )
            store.acknowledge(event_id, acknowledgement(body), read_back_body=body)
            self.assertEqual(store.status(event_id)["user_state"], ACKNOWLEDGED)

    def test_corrupt_compacted_evidence_blocks_every_later_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "device.sqlite3"
            store = OutboxStore(database)
            first = envelope_bytes(3)
            first_id = store.save(first)
            store.acknowledge(first_id, acknowledgement(first), read_back_body=first)
            self.assertEqual(store.clear_verified_payloads(), 1)
            self.assertIsNone(store.payload(first_id))

            second = envelope_bytes(4)
            second_id = store.save(second)
            store.acknowledge(second_id, acknowledgement(second, 2), read_back_body=second)
            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE authority_records SET data = ? WHERE kind = 'device_compaction'",
                    (b'{"malformed":true}',),
                )

            with self.assertRaises(ClearBlocked):
                store.clear_verified_payloads()
            self.assertEqual(store.payload(second_id), second)
            self.assertEqual(store.status(first_id)["user_state"], CONFLICT)

    def test_asymmetric_missing_payload_and_malformed_ack_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "device.sqlite3"
            store = OutboxStore(database)
            first = envelope_bytes(5)
            first_id = store.save(first)
            store.acknowledge(first_id, acknowledgement(first), read_back_body=first)
            second = envelope_bytes(6)
            second_id = store.save(second)
            store.acknowledge(second_id, acknowledgement(second, 2), read_back_body=second)

            with sqlite3.connect(database) as connection:
                connection.execute("DELETE FROM authority_payloads WHERE event_id = ?", (first_id,))
            with self.assertRaises(ClearBlocked):
                store.clear_verified_payloads()
            self.assertEqual(store.payload(second_id), second)

            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE authority_records SET data = ? WHERE kind = 'device_ack' AND subject_id = ?",
                    (b'{"acknowledgement_json":', second_id),
                )
            self.assertEqual(store.status(second_id)["user_state"], CONFLICT)

    def test_compaction_metadata_is_rehashed_validated_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database = Path(temporary_directory) / "device.sqlite3"
            store = OutboxStore(database)
            body = envelope_bytes(7)
            event_id = store.save(body)
            store.acknowledge(event_id, acknowledgement(body), read_back_body=body)
            store.clear_verified_payloads()
            metadata = store.compaction_events(event_id)[0]
            self.assertEqual(set(metadata), {
                "event_id", "body_sha256", "body_bytes", "commit_record_hash", "ack_record_hash"
            })
            self.assertLess(len(json.dumps(metadata)), 1024)

            with sqlite3.connect(database) as connection:
                connection.execute(
                    "UPDATE authority_records SET data = ? WHERE kind = 'device_compaction'",
                    (json.dumps({**metadata, "padding": "x" * 2048}).encode(),),
                )
            self.assertEqual(store.status(event_id)["user_state"], CONFLICT)
            with self.assertRaises(ClearBlocked):
                store.clear_verified_payloads()

    def test_process_termination_at_each_device_durable_boundary_is_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            body = envelope_bytes(8)
            body_path = root / "body.json"
            body_path.write_bytes(body)
            event_id = json.loads(body)["event_id"]

            for operation, failpoint, code, expected_state in (
                ("save", "before_commit", 91, CREATED),
                ("save", "after_commit", 92, DURABLE_QUEUED),
                ("ack", "before_commit", 93, DURABLE_QUEUED),
                ("ack", "after_commit", 94, ACKNOWLEDGED),
                ("clear", "before_commit", 95, ACKNOWLEDGED),
                ("clear", "after_commit", 96, ACKNOWLEDGED),
            ):
                with self.subTest(operation=operation, failpoint=failpoint):
                    database = root / f"{operation}-{failpoint}.sqlite3"
                    if operation != "save":
                        setup = OutboxStore(database)
                        setup.save(body)
                        if operation == "clear":
                            setup.acknowledge(event_id, acknowledgement(body), read_back_body=body)
                    completed = self._crash(database, body_path, operation, failpoint)
                    self.assertEqual(completed.returncode, code, completed.stderr)
                    reopened = OutboxStore(database)
                    self.assertEqual(reopened.status(event_id)["user_state"], expected_state)
                    if expected_state == CREATED or (
                        operation == "clear" and failpoint == "after_commit"
                    ):
                        self.assertIsNone(reopened.payload(event_id))
                    else:
                        self.assertEqual(reopened.payload(event_id), body)

    @staticmethod
    def _crash(
        database: Path, body_path: Path, operation: str, failpoint: str
    ) -> subprocess.CompletedProcess[str]:
        program = f"""
import hashlib, json, sys
sys.path[:0] = [{str(CONTRACTS)!r}, {str(SYNC_CLIENT)!r}]
from outbox import OutboxStore
body = open({str(body_path)!r}, 'rb').read()
event_id = json.loads(body)['event_id']
store = OutboxStore({str(database)!r})
ack = {{
    'ack_version': 'mhpss.ack/2.0', 'status': 'accepted', 'event_id': event_id,
    'accepted_body_sha256': hashlib.sha256(body).hexdigest(),
    'accepted_body_bytes': len(body), 'canonical_sequence': 1,
    'contract_version': 'mhpss.event/2.0'
}}
if {operation!r} == 'save': store.save(body, crash_at={failpoint!r})
elif {operation!r} == 'ack': store.acknowledge(event_id, ack, read_back_body=body, crash_at={failpoint!r})
else: store.clear_verified_payloads(crash_at={failpoint!r})
"""
        return subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
