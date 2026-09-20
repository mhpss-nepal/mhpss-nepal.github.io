#!/usr/bin/env python3
"""Immutable, byte-rehashed device commit-log authority."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from mhpss_v2 import CONTRACT_VERSION, parse_envelope
from sync_states import ACKNOWLEDGED as USER_ACKNOWLEDGED
from sync_states import CONFLICT as USER_CONFLICT
from sync_states import CREATED
from sync_states import DURABLE_QUEUED

PENDING = "pending"
ACKNOWLEDGED = "acknowledged"
CONFLICT = "conflict"
ACK_VERSION = "mhpss.ack/2.0"
MAX_AUTHORITY_RECORD_BYTES = 524_288
MAX_COMPACTION_RECORD_BYTES = 1_024


class OutboxError(RuntimeError):
    """Base error for local immutable-authority failures."""


class AcknowledgementError(OutboxError):
    """The server acknowledgement does not prove acceptance of exact bytes."""


class ClearBlocked(OutboxError):
    """Payload removal would strand an unresolved or unverifiable obligation."""


class OutboxStore:
    """A hash-chained commit log plus recoverable payload storage."""

    def __init__(self, database: str | Path):
        self.database = str(database)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
        for attempt in range(100):
            try:
                connection.execute("PRAGMA journal_mode = WAL")
                break
            except sqlite3.OperationalError as error:
                if "locked" not in str(error).lower() or attempt == 99:
                    connection.close()
                    raise
                time.sleep(0.01)
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS authority_records (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    previous_hash TEXT,
                    data BLOB NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS authority_payloads (
                    event_id TEXT PRIMARY KEY,
                    body BLOB NOT NULL
                );
                """
            )
        finally:
            connection.close()

    def save(self, body: bytes, *, crash_at: str | None = None) -> str:
        envelope = parse_envelope(body)
        event_id = envelope["event_id"]
        digest = hashlib.sha256(body).hexdigest()
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            records = self._validated_records(connection)
            commit = self._record_for(records, "device_commit", event_id)
            if commit is not None:
                accepted_digest = commit["value"]["body_sha256"]
                if accepted_digest != digest:
                    self._append_conflict(
                        connection,
                        event_id=event_id,
                        reason="EVENT_ID_BODY_CONFLICT",
                        accepted_digest=accepted_digest,
                        incoming_body=body,
                    )
                    connection.commit()
                    raise OutboxError("event_id is already bound to different immutable bytes")
                self._assert_event_recoverable(records, connection, event_id)
                if self._event_state(records, event_id) == CONFLICT:
                    raise OutboxError("durable conflict requires explicit audited recovery")
                connection.rollback()
                return event_id

            connection.execute(
                "INSERT INTO authority_payloads (event_id, body) VALUES (?, ?)",
                (event_id, body),
            )
            self._append_record(
                connection,
                "device_commit",
                event_id,
                {
                    "event_id": event_id,
                    "body_sha256": digest,
                    "body_bytes": len(body),
                    "contract_version": CONTRACT_VERSION,
                },
            )
            if crash_at == "before_commit":
                os._exit(91)
            connection.commit()
            if crash_at == "after_commit":
                os._exit(92)
            return event_id
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def acknowledge(
        self,
        event_id: str,
        acknowledgement: dict[str, Any],
        *,
        read_back_body: bytes | None,
        crash_at: str | None = None,
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            records = self._validated_records(connection)
            commit = self._record_for(records, "device_commit", event_id)
            if commit is None:
                raise AcknowledgementError("no local durable obligation exists for event_id")
            self._assert_event_recoverable(records, connection, event_id)
            if self._event_state(records, event_id) == CONFLICT:
                raise AcknowledgementError("conflict requires explicit audited recovery")

            body = self._payload(connection, event_id)
            expected = commit["value"]
            try:
                encoded = self._validate_ack(
                    event_id, expected, acknowledgement, body, read_back_body
                )
            except AcknowledgementError as error:
                incoming_body = self._incoming_ack_bytes(acknowledgement, read_back_body)
                self._append_conflict(
                    connection,
                    event_id=event_id,
                    reason="ACKNOWLEDGEMENT_MISMATCH",
                    accepted_digest=expected["body_sha256"],
                    incoming_body=incoming_body,
                )
                connection.commit()
                raise error

            prior_ack = self._record_for(records, "device_ack", event_id)
            ack_value = {
                "event_id": event_id,
                "commit_record_hash": commit["record_hash"],
                "acknowledgement_json_b64": base64.b64encode(encoded).decode("ascii"),
            }
            if prior_ack is not None:
                if prior_ack["value"] != ack_value:
                    self._append_conflict(
                        connection,
                        event_id=event_id,
                        reason="ACKNOWLEDGEMENT_REPLAY_CONFLICT",
                        accepted_digest=expected["body_sha256"],
                        incoming_body=encoded,
                    )
                    connection.commit()
                    raise AcknowledgementError(
                        "acknowledgement replay differs from immutable authority"
                    )
                if self._event_state(records, event_id) == ACKNOWLEDGED:
                    connection.rollback()
                    return
            self._append_record(connection, "device_ack", event_id, ack_value)
            if crash_at == "before_commit":
                os._exit(93)
            connection.commit()
            if crash_at == "after_commit":
                os._exit(94)
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def record_recovery(self, event_id: str, *, actor: str, reason: str) -> str:
        self._bounded_text(actor, "actor")
        self._bounded_text(reason, "reason")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            records = self._validated_records(connection)
            conflict = self._latest_record(records, "device_conflict", event_id)
            if conflict is None or self._event_state(records, event_id) != CONFLICT:
                raise OutboxError("no unresolved durable conflict exists")
            record_hash = self._append_record(
                connection,
                "device_recovery",
                event_id,
                {
                    "event_id": event_id,
                    "actor": actor,
                    "reason": reason,
                    "recovered_conflict_hash": conflict["record_hash"],
                },
            )
            connection.commit()
            return record_hash
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def clear_verified_payloads(self, *, crash_at: str | None = None) -> int:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            records = self._validated_records(connection)
            event_ids = [
                record["subject_id"] for record in records if record["kind"] == "device_commit"
            ]
            for event_id in event_ids:
                self._assert_event_recoverable(records, connection, event_id)
                if self._event_state(records, event_id) != ACKNOWLEDGED:
                    raise ClearBlocked("clear refused: unresolved outbox obligations exist")

            payload_ids = [
                row["event_id"]
                for row in connection.execute(
                    "SELECT event_id FROM authority_payloads ORDER BY rowid"
                )
            ]
            for event_id in payload_ids:
                commit = self._record_for(records, "device_commit", event_id)
                ack = self._record_for(records, "device_ack", event_id)
                if commit is None or ack is None:
                    raise ClearBlocked("clear refused: terminal authority is incomplete")
                value = {
                    "event_id": event_id,
                    "body_sha256": commit["value"]["body_sha256"],
                    "body_bytes": commit["value"]["body_bytes"],
                    "commit_record_hash": commit["record_hash"],
                    "ack_record_hash": ack["record_hash"],
                }
                encoded = self._canonical(value)
                if len(encoded) > MAX_COMPACTION_RECORD_BYTES:
                    raise ClearBlocked("clear refused: compaction evidence exceeds its bound")
                self._append_record(connection, "device_compaction", event_id, value)
                connection.execute(
                    "DELETE FROM authority_payloads WHERE event_id = ?", (event_id,)
                )
            if crash_at == "before_commit":
                os._exit(95)
            connection.commit()
            if crash_at == "after_commit":
                os._exit(96)
            return len(payload_ids)
        except ClearBlocked:
            if connection.in_transaction:
                connection.rollback()
            raise
        except OutboxError as error:
            if connection.in_transaction:
                connection.rollback()
            raise ClearBlocked(str(error)) from error
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def compact_acknowledged(self, *, max_payload_rows: int, max_payload_bytes: int) -> int:
        if max_payload_rows < 0 or max_payload_bytes < 0:
            raise ValueError("compaction bounds must be non-negative")
        connection = self._connect()
        try:
            rows = list(
                connection.execute(
                    "SELECT event_id, length(body) AS body_bytes FROM authority_payloads ORDER BY rowid"
                )
            )
        finally:
            connection.close()
        selected = list(rows)
        while selected and (
            len(selected) > max_payload_rows
            or sum(row["body_bytes"] for row in selected) > max_payload_bytes
        ):
            selected.pop(0)
        remove_count = len(rows) - len(selected)
        if remove_count == 0:
            return 0
        # A single atomic clear is intentionally stricter than selective deletion.
        if remove_count != len(rows):
            raise OutboxError("partial compaction is not an approved recovery boundary")
        return self.clear_verified_payloads()

    def status(self, event_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            try:
                records = self._validated_records(connection)
                commit = self._record_for(records, "device_commit", event_id)
                if commit is None:
                    return {"user_state": CREATED, "event_id": event_id}
                self._assert_event_recoverable(records, connection, event_id)
                state = self._event_state(records, event_id)
                user_state = (
                    USER_CONFLICT
                    if state == CONFLICT
                    else USER_ACKNOWLEDGED
                    if state == ACKNOWLEDGED
                    else DURABLE_QUEUED
                )
                return {"user_state": user_state, "event_id": event_id}
            except (OutboxError, ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError):
                return {"user_state": USER_CONFLICT, "event_id": event_id}
        finally:
            connection.close()

    def pending_bodies(self) -> list[bytes]:
        connection = self._connect()
        try:
            records = self._validated_records(connection)
            bodies: list[bytes] = []
            for record in records:
                if record["kind"] != "device_commit":
                    continue
                event_id = record["subject_id"]
                self._assert_event_recoverable(records, connection, event_id)
                if self._event_state(records, event_id) == PENDING:
                    body = self._payload(connection, event_id)
                    if body is None:
                        raise OutboxError("pending obligation is missing recoverable payload")
                    bodies.append(body)
            return bodies
        finally:
            connection.close()

    def payload(self, event_id: str) -> bytes | None:
        connection = self._connect()
        try:
            return self._payload(connection, event_id)
        finally:
            connection.close()

    def source_body(self, event_id: str) -> bytes | None:
        return self.payload(event_id)

    def outbox_item(self, event_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            records = self._validated_records(connection)
            if self._record_for(records, "device_commit", event_id) is None:
                return None
            state = self._event_state(records, event_id)
            return {"event_id": event_id, "body": self._payload(connection, event_id), "state": state}
        except OutboxError:
            return {"event_id": event_id, "body": self._payload(connection, event_id), "state": CONFLICT}
        finally:
            connection.close()

    def receipt(self, event_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            records = self._validated_records(connection)
            ack = self._record_for(records, "device_ack", event_id)
            if ack is None:
                return None
            decoded = json.loads(base64.b64decode(ack["value"]["acknowledgement_json_b64"]))
            return {
                "event_id": event_id,
                "body_sha256": decoded["accepted_body_sha256"],
                "body_bytes": decoded["accepted_body_bytes"],
                "canonical_sequence": decoded["canonical_sequence"],
                "contract_version": decoded["contract_version"],
            }
        except (OutboxError, ValueError, KeyError, json.JSONDecodeError):
            return None
        finally:
            connection.close()

    def conflict_count(self, event_id: str) -> int:
        connection = self._connect()
        try:
            records = self._validated_records(connection)
            return sum(
                record["kind"] == "device_conflict" and record["subject_id"] == event_id
                for record in records
            )
        finally:
            connection.close()

    def latest_conflict_body(self, event_id: str) -> bytes | None:
        connection = self._connect()
        try:
            record = self._latest_record(
                self._validated_records(connection), "device_conflict", event_id
            )
            if record is None:
                return None
            return base64.b64decode(record["value"]["incoming_body_b64"], validate=True)
        finally:
            connection.close()

    def latest_conflict_digest(self, event_id: str) -> str | None:
        connection = self._connect()
        try:
            record = self._latest_record(
                self._validated_records(connection), "device_conflict", event_id
            )
            return None if record is None else record["value"]["incoming_sha256"]
        finally:
            connection.close()

    def recovery_events(self, event_id: str) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            return [
                dict(record["value"])
                for record in self._validated_records(connection)
                if record["kind"] == "device_recovery" and record["subject_id"] == event_id
            ]
        finally:
            connection.close()

    def compaction_events(self, event_id: str) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            return [
                dict(record["value"])
                for record in self._validated_records(connection)
                if record["kind"] == "device_compaction" and record["subject_id"] == event_id
            ]
        finally:
            connection.close()

    def reset_conflict_for_retry(self, event_id: str) -> None:
        self.record_recovery(
            event_id,
            actor="legacy-test-adapter",
            reason="explicit compatibility recovery action",
        )

    def counts(self) -> dict[str, int]:
        connection = self._connect()
        try:
            records = self._validated_records(connection)
            commits = sum(record["kind"] == "device_commit" for record in records)
            acknowledgements = sum(record["kind"] == "device_ack" for record in records)
            return {"sources": commits, "outbox": commits, "receipts": acknowledgements}
        finally:
            connection.close()

    def integrity_check(self) -> str:
        connection = self._connect()
        try:
            sqlite_result = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if sqlite_result != "ok":
                return sqlite_result
            self._validated_records(connection)
            return "ok"
        finally:
            connection.close()

    @classmethod
    def _validated_records(cls, connection: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = list(connection.execute("SELECT * FROM authority_records ORDER BY sequence"))
        records: list[dict[str, Any]] = []
        previous_hash: str | None = None
        for expected_sequence, row in enumerate(rows, start=1):
            data = bytes(row["data"])
            if row["sequence"] != expected_sequence or len(data) > MAX_AUTHORITY_RECORD_BYTES:
                raise OutboxError("immutable authority sequence or size bound is invalid")
            if row["previous_hash"] != previous_hash:
                raise OutboxError("immutable authority chain is broken")
            calculated = cls._record_digest(previous_hash, row["kind"], row["subject_id"], data)
            if row["record_hash"] != calculated:
                raise OutboxError("immutable authority record hash mismatch")
            try:
                value = cls._strict_json(data)
            except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as error:
                raise OutboxError("immutable authority record JSON is invalid") from error
            if not isinstance(value, dict) or value.get("event_id") != row["subject_id"]:
                raise OutboxError("immutable authority record subject is invalid")
            records.append(
                {
                    "sequence": row["sequence"],
                    "kind": row["kind"],
                    "subject_id": row["subject_id"],
                    "record_hash": row["record_hash"],
                    "value": value,
                }
            )
            previous_hash = calculated
        cls._validate_semantics(records)
        return records

    @classmethod
    def _validate_semantics(cls, records: list[dict[str, Any]]) -> None:
        commits: dict[str, dict[str, Any]] = {}
        acknowledgements: dict[str, dict[str, Any]] = {}
        latest_conflicts: dict[str, str] = {}
        recovered: set[str] = set()
        compacted: set[str] = set()
        for record in records:
            event_id = record["subject_id"]
            value = record["value"]
            if record["kind"] == "device_commit":
                if event_id in commits or set(value) != {
                    "event_id", "body_sha256", "body_bytes", "contract_version"
                }:
                    raise OutboxError("device commit authority is malformed or duplicated")
                if value["contract_version"] != CONTRACT_VERSION or not cls._is_digest(
                    value["body_sha256"]
                ):
                    raise OutboxError("device commit authority is invalid")
                if isinstance(value["body_bytes"], bool) or not isinstance(value["body_bytes"], int) or value["body_bytes"] < 1:
                    raise OutboxError("device commit byte count is invalid")
                commits[event_id] = record
            elif record["kind"] == "device_conflict":
                if event_id not in commits or not cls._is_digest(value.get("incoming_sha256")):
                    raise OutboxError("device conflict authority is invalid")
                incoming = base64.b64decode(value["incoming_body_b64"], validate=True)
                if hashlib.sha256(incoming).hexdigest() != value["incoming_sha256"]:
                    raise OutboxError("device conflict incoming bytes do not match their digest")
                latest_conflicts[event_id] = record["record_hash"]
                recovered.discard(event_id)
            elif record["kind"] == "device_recovery":
                if value.get("recovered_conflict_hash") != latest_conflicts.get(event_id):
                    raise OutboxError("device recovery does not target the latest conflict")
                cls._bounded_text(value.get("actor"), "actor")
                cls._bounded_text(value.get("reason"), "reason")
                recovered.add(event_id)
            elif record["kind"] == "device_ack":
                commit = commits.get(event_id)
                if commit is None or value.get("commit_record_hash") != commit["record_hash"]:
                    raise OutboxError("device acknowledgement is not commit-bound")
                try:
                    ack_bytes = base64.b64decode(value["acknowledgement_json_b64"], validate=True)
                    ack = cls._strict_json(ack_bytes)
                except (ValueError, KeyError, UnicodeError, json.JSONDecodeError) as error:
                    raise OutboxError("device acknowledgement JSON is invalid") from error
                cls._validate_ack_value(event_id, commit["value"], ack)
                if event_id in acknowledgements and acknowledgements[event_id]["value"] != value:
                    raise OutboxError("device acknowledgement authority is duplicated")
                acknowledgements[event_id] = record
            elif record["kind"] == "device_compaction":
                encoded = cls._canonical(value)
                commit = commits.get(event_id)
                ack = acknowledgements.get(event_id)
                if (
                    len(encoded) > MAX_COMPACTION_RECORD_BYTES
                    or commit is None
                    or ack is None
                    or value != {
                        "event_id": event_id,
                        "body_sha256": commit["value"]["body_sha256"],
                        "body_bytes": commit["value"]["body_bytes"],
                        "commit_record_hash": commit["record_hash"],
                        "ack_record_hash": ack["record_hash"],
                    }
                    or event_id in compacted
                ):
                    raise OutboxError("device compaction authority is invalid")
                compacted.add(event_id)
            else:
                raise OutboxError(f"unknown immutable authority record kind: {record['kind']}")

    @classmethod
    def _assert_event_recoverable(
        cls,
        records: list[dict[str, Any]],
        connection: sqlite3.Connection,
        event_id: str,
    ) -> None:
        commit = cls._record_for(records, "device_commit", event_id)
        if commit is None:
            raise OutboxError("device commit authority is missing")
        payload = cls._payload(connection, event_id)
        compaction = cls._record_for(records, "device_compaction", event_id)
        if payload is None:
            if compaction is None:
                raise OutboxError("last recoverable payload is missing without compaction evidence")
            return
        if compaction is not None:
            raise OutboxError("payload exists after terminal compaction authority")
        if (
            len(payload) != commit["value"]["body_bytes"]
            or hashlib.sha256(payload).hexdigest() != commit["value"]["body_sha256"]
        ):
            raise OutboxError("recoverable payload bytes do not match immutable authority")
        try:
            envelope = parse_envelope(payload)
        except Exception as error:
            raise OutboxError("recoverable payload is not a valid canonical envelope") from error
        if envelope["event_id"] != event_id:
            raise OutboxError("recoverable payload identity differs from authority")

    @classmethod
    def _event_state(cls, records: list[dict[str, Any]], event_id: str) -> str:
        state = PENDING
        for record in records:
            if record["subject_id"] != event_id:
                continue
            if record["kind"] == "device_conflict":
                state = CONFLICT
            elif record["kind"] == "device_recovery":
                state = PENDING
            elif record["kind"] == "device_ack" and state != CONFLICT:
                state = ACKNOWLEDGED
        return state

    @staticmethod
    def _validate_ack(
        event_id: str,
        commit: dict[str, Any],
        acknowledgement: dict[str, Any],
        body: bytes | None,
        read_back_body: bytes | None,
    ) -> bytes:
        try:
            encoded = OutboxStore._canonical(acknowledgement)
        except (TypeError, ValueError) as error:
            raise AcknowledgementError("acknowledgement is not canonical finite JSON") from error
        OutboxStore._validate_ack_value(event_id, commit, acknowledgement)
        if body is None:
            raise AcknowledgementError("local recoverable body is unavailable")
        if (
            len(body) != commit["body_bytes"]
            or hashlib.sha256(body).hexdigest() != commit["body_sha256"]
        ):
            raise AcknowledgementError("local recoverable body no longer matches authority")
        if read_back_body is None:
            raise AcknowledgementError("canonical exact-body read-back is required")
        if (
            len(read_back_body) != commit["body_bytes"]
            or hashlib.sha256(read_back_body).hexdigest() != commit["body_sha256"]
        ):
            raise AcknowledgementError("canonical read-back does not match exact queued body")
        return encoded

    @staticmethod
    def _validate_ack_value(
        event_id: str, commit: dict[str, Any], acknowledgement: object
    ) -> None:
        required = {
            "ack_version", "status", "event_id", "accepted_body_sha256",
            "accepted_body_bytes", "canonical_sequence", "contract_version",
        }
        if not isinstance(acknowledgement, dict) or set(acknowledgement) != required:
            raise AcknowledgementError("acknowledgement fields are incomplete or unknown")
        expected = {
            "ack_version": ACK_VERSION,
            "status": "accepted",
            "event_id": event_id,
            "accepted_body_sha256": commit["body_sha256"],
            "accepted_body_bytes": commit["body_bytes"],
            "contract_version": CONTRACT_VERSION,
        }
        if any(acknowledgement.get(key) != value for key, value in expected.items()):
            raise AcknowledgementError("acknowledgement does not match immutable commit")
        sequence = acknowledgement["canonical_sequence"]
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise AcknowledgementError("canonical_sequence must be a positive integer")

    @classmethod
    def _append_conflict(
        cls,
        connection: sqlite3.Connection,
        *,
        event_id: str,
        reason: str,
        accepted_digest: str,
        incoming_body: bytes,
    ) -> str:
        return cls._append_record(
            connection,
            "device_conflict",
            event_id,
            {
                "event_id": event_id,
                "reason_code": reason,
                "accepted_body_sha256": accepted_digest,
                "incoming_sha256": hashlib.sha256(incoming_body).hexdigest(),
                "incoming_body_b64": base64.b64encode(incoming_body).decode("ascii"),
            },
        )

    @classmethod
    def _append_record(
        cls,
        connection: sqlite3.Connection,
        kind: str,
        subject_id: str,
        value: dict[str, Any],
    ) -> str:
        data = cls._canonical(value)
        if len(data) > MAX_AUTHORITY_RECORD_BYTES:
            raise OutboxError("immutable authority record exceeds its bound")
        prior = connection.execute(
            "SELECT record_hash FROM authority_records ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = None if prior is None else prior["record_hash"]
        record_hash = cls._record_digest(previous_hash, kind, subject_id, data)
        connection.execute(
            """
            INSERT INTO authority_records (kind, subject_id, previous_hash, data, record_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            (kind, subject_id, previous_hash, data, record_hash),
        )
        return record_hash

    @staticmethod
    def _record_digest(previous_hash: str | None, kind: str, subject_id: str, data: bytes) -> str:
        previous = b"" if previous_hash is None else bytes.fromhex(previous_hash)
        framed = (
            len(previous).to_bytes(2, "big") + previous
            + len(kind.encode()).to_bytes(2, "big") + kind.encode()
            + len(subject_id.encode()).to_bytes(2, "big") + subject_id.encode()
            + len(data).to_bytes(8, "big") + data
        )
        return hashlib.sha256(framed).hexdigest()

    @staticmethod
    def _canonical(value: object) -> bytes:
        return json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")

    @classmethod
    def _strict_json(cls, data: bytes) -> Any:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=cls._unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
        if cls._canonical(value) != data:
            raise ValueError("authority JSON is not canonical")
        return value

    @staticmethod
    def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    @staticmethod
    def _payload(connection: sqlite3.Connection, event_id: str) -> bytes | None:
        row = connection.execute(
            "SELECT body FROM authority_payloads WHERE event_id = ?", (event_id,)
        ).fetchone()
        return None if row is None else bytes(row["body"])

    @staticmethod
    def _record_for(
        records: list[dict[str, Any]], kind: str, event_id: str
    ) -> dict[str, Any] | None:
        matches = [
            record for record in records
            if record["kind"] == kind and record["subject_id"] == event_id
        ]
        return None if not matches else matches[0]

    @staticmethod
    def _latest_record(
        records: list[dict[str, Any]], kind: str, event_id: str
    ) -> dict[str, Any] | None:
        matches = [
            record for record in records
            if record["kind"] == kind and record["subject_id"] == event_id
        ]
        return None if not matches else matches[-1]

    @staticmethod
    def _incoming_ack_bytes(
        acknowledgement: dict[str, Any], read_back_body: bytes | None
    ) -> bytes:
        try:
            acknowledgement_bytes = OutboxStore._canonical(acknowledgement)
        except (TypeError, ValueError):
            acknowledgement_bytes = repr(acknowledgement).encode("utf-8", "backslashreplace")
        return acknowledgement_bytes + b"\n" + (b"" if read_back_body is None else read_back_body)

    @staticmethod
    def _bounded_text(value: object, label: str) -> None:
        if not isinstance(value, str) or not value or len(value) > 512:
            raise OutboxError(f"{label} must be a non-empty string of at most 512 characters")
        if any(ord(character) < 0x20 for character in value):
            raise OutboxError(f"{label} contains a control character")

    @staticmethod
    def _is_digest(value: object) -> bool:
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )