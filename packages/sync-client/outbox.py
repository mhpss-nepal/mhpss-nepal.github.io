#!/usr/bin/env python3
"""SQLite reference for a transactional device source/outbox boundary."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from mhpss_v2 import CONTRACT_VERSION, parse_envelope

PENDING = "pending"
ACKNOWLEDGED = "acknowledged"
CONFLICT = "conflict"
ACK_VERSION = "mhpss.ack/1.0"


class OutboxError(RuntimeError):
    """Base error for local sync-contract failures."""


class AcknowledgementError(OutboxError):
    """The server receipt does not prove acceptance of the exact body."""


class ClearBlocked(OutboxError):
    """Local payload removal would strand an unresolved obligation."""


class OutboxStore:
    """One durable local transaction for source and exact outbox bytes."""

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
                CREATE TABLE IF NOT EXISTS source_events (
                    event_id TEXT PRIMARY KEY,
                    body BLOB,
                    body_sha256 TEXT NOT NULL,
                    body_bytes INTEGER NOT NULL,
                    created_order INTEGER NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    event_id TEXT PRIMARY KEY REFERENCES source_events(event_id),
                    body BLOB,
                    body_sha256 TEXT NOT NULL,
                    body_bytes INTEGER NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('pending', 'acknowledged', 'conflict')),
                    created_order INTEGER NOT NULL UNIQUE,
                    acknowledgement_json BLOB
                );
                CREATE TABLE IF NOT EXISTS receipts (
                    event_id TEXT PRIMARY KEY,
                    body_sha256 TEXT NOT NULL,
                    body_bytes INTEGER NOT NULL,
                    canonical_sequence INTEGER NOT NULL,
                    contract_version TEXT NOT NULL,
                    acknowledgement_json BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conflict_evidence (
                    conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    accepted_body_sha256 TEXT NOT NULL,
                    incoming_sha256 TEXT NOT NULL,
                    incoming_body BLOB NOT NULL,
                    details_json BLOB NOT NULL,
                    UNIQUE(event_id, reason_code, incoming_sha256)
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
            prior = connection.execute(
                """
                SELECT s.body_sha256 AS source_sha256, s.body_bytes AS source_bytes,
                       s.created_order AS source_order, s.body AS source_body,
                       o.body_sha256 AS outbox_sha256, o.body_bytes AS outbox_bytes,
                       o.created_order AS outbox_order, o.body AS outbox_body,
                       o.state AS outbox_state, o.acknowledgement_json
                FROM source_events s LEFT JOIN outbox o ON o.event_id = s.event_id
                WHERE s.event_id = ?
                """,
                (event_id,),
            ).fetchone()
            if prior is not None:
                prior_body = None if prior["source_body"] is None else bytes(prior["source_body"])
                if prior["source_sha256"] != digest or (
                    prior_body is not None and prior_body != body
                ):
                    self._record_conflict(
                        connection,
                        event_id=event_id,
                        reason="EVENT_ID_BODY_CONFLICT",
                        accepted_digest=prior["source_sha256"],
                        incoming_digest=digest,
                        incoming_body=body,
                    )
                    connection.commit()
                    raise OutboxError("event_id is already bound to different immutable bytes")
                if (
                    prior["outbox_state"] is None
                    or prior["outbox_sha256"] != prior["source_sha256"]
                    or prior["outbox_bytes"] != prior["source_bytes"]
                    or prior["outbox_order"] != prior["source_order"]
                ):
                    raise OutboxError("source/outbox invariant is broken")
                outbox_body = None if prior["outbox_body"] is None else bytes(prior["outbox_body"])
                if (prior_body is None) != (outbox_body is None) or (
                    prior_body is not None and outbox_body != prior_body
                ):
                    raise OutboxError("source/outbox invariant is broken")
                if prior["outbox_state"] == CONFLICT:
                    raise OutboxError("durable conflict requires explicit recovery")
                if prior["outbox_state"] == ACKNOWLEDGED and not self._terminal_evidence_valid(
                    connection, event_id
                ):
                    raise OutboxError("terminal evidence is invalid")
                if prior_body is None:
                    if prior["outbox_state"] != ACKNOWLEDGED or not self._terminal_evidence_valid(
                        connection, event_id
                    ):
                        raise OutboxError("compacted event lacks verified terminal evidence")
                connection.rollback()
                return event_id
            next_order = connection.execute(
                "SELECT COALESCE(MAX(created_order), 0) + 1 FROM source_events"
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO source_events VALUES (?, ?, ?, ?, ?)",
                (event_id, body, digest, len(body), next_order),
            )
            connection.execute(
                "INSERT INTO outbox VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (event_id, body, digest, len(body), PENDING, next_order),
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
    ) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT body, body_sha256, body_bytes, state FROM outbox WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if row is None:
                raise AcknowledgementError("no local outbox obligation exists for event_id")
            body = None if row["body"] is None else bytes(row["body"])
            try:
                self._validate_ack(event_id, row, acknowledgement, body, read_back_body)
            except AcknowledgementError as error:
                incoming = hashlib.sha256(
                    json.dumps(
                        acknowledgement, default=repr, separators=(",", ":"), sort_keys=True
                    ).encode("utf-8")
                    + (b"" if read_back_body is None else read_back_body)
                ).hexdigest()
                self._record_conflict(
                    connection,
                    event_id=event_id,
                    reason="ACKNOWLEDGEMENT_MISMATCH",
                    accepted_digest=row["body_sha256"],
                    incoming_digest=incoming,
                    incoming_body=(
                        json.dumps(
                            acknowledgement, default=repr, separators=(",", ":"), sort_keys=True
                        ).encode("utf-8")
                        + b"\n"
                        + (b"" if read_back_body is None else read_back_body)
                    ),
                )
                connection.commit()
                raise error
            encoded = json.dumps(
                acknowledgement, separators=(",", ":"), sort_keys=True, allow_nan=False
            ).encode("utf-8")
            receipt = connection.execute(
                "SELECT * FROM receipts WHERE event_id = ?", (event_id,)
            ).fetchone()
            receipt_values = (
                event_id,
                row["body_sha256"],
                row["body_bytes"],
                acknowledgement["canonical_sequence"],
                acknowledgement["contract_version"],
                encoded,
            )
            if receipt is None:
                connection.execute("INSERT INTO receipts VALUES (?, ?, ?, ?, ?, ?)", receipt_values)
            elif (
                receipt["body_sha256"] != row["body_sha256"]
                or receipt["body_bytes"] != row["body_bytes"]
                or receipt["canonical_sequence"] != acknowledgement["canonical_sequence"]
                or receipt["contract_version"] != acknowledgement["contract_version"]
                or bytes(receipt["acknowledgement_json"]) != encoded
            ):
                self._record_conflict(
                    connection,
                    event_id=event_id,
                    reason="ACKNOWLEDGEMENT_REPLAY_CONFLICT",
                    accepted_digest=receipt["body_sha256"],
                    incoming_digest=hashlib.sha256(encoded).hexdigest(),
                    incoming_body=encoded,
                )
                connection.commit()
                raise AcknowledgementError("acknowledgement replay differs from durable receipt")
            connection.execute(
                "UPDATE outbox SET state = ?, acknowledgement_json = ? WHERE event_id = ?",
                (ACKNOWLEDGED, encoded, event_id),
            )
            connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _validate_ack(
        event_id: str,
        row: sqlite3.Row,
        acknowledgement: dict[str, Any],
        body: bytes | None,
        read_back_body: bytes | None,
    ) -> None:
        required = {
            "ack_version",
            "status",
            "event_id",
            "accepted_body_sha256",
            "accepted_body_bytes",
            "canonical_sequence",
            "contract_version",
        }
        if not isinstance(acknowledgement, dict) or set(acknowledgement) != required:
            raise AcknowledgementError("acknowledgement fields are incomplete or unknown")
        expected = {
            "ack_version": ACK_VERSION,
            "status": "accepted",
            "event_id": event_id,
            "accepted_body_sha256": row["body_sha256"],
            "accepted_body_bytes": row["body_bytes"],
            "contract_version": CONTRACT_VERSION,
        }
        for key, value in expected.items():
            if acknowledgement.get(key) != value:
                raise AcknowledgementError(f"acknowledgement does not match exact body: {key}")
        sequence = acknowledgement["canonical_sequence"]
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise AcknowledgementError("canonical_sequence must be a positive integer")
        if body is not None and hashlib.sha256(body).hexdigest() != row["body_sha256"]:
            raise AcknowledgementError("local outbox body no longer matches its stored digest")
        if read_back_body is None:
            raise AcknowledgementError("canonical exact-body read-back is required")
        if (
            len(read_back_body) != row["body_bytes"]
            or hashlib.sha256(read_back_body).hexdigest() != row["body_sha256"]
        ):
            raise AcknowledgementError("canonical read-back does not match the exact queued body")

    def clear_verified_payloads(self) -> int:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._assert_no_orphans(connection, error_type=ClearBlocked)
            unresolved = connection.execute(
                "SELECT COUNT(*) FROM outbox WHERE state != ? OR acknowledgement_json IS NULL",
                (ACKNOWLEDGED,),
            ).fetchone()[0]
            if unresolved:
                raise ClearBlocked("clear refused: unresolved outbox obligations exist")
            event_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT event_id FROM outbox WHERE body IS NOT NULL ORDER BY created_order"
                )
            ]
            for event_id in event_ids:
                if not self._terminal_evidence_valid(connection, event_id):
                    raise ClearBlocked("clear refused: terminal evidence is invalid")
            connection.execute("UPDATE outbox SET body = NULL WHERE body IS NOT NULL")
            connection.execute("UPDATE source_events SET body = NULL")
            connection.commit()
            return len(event_ids)
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
            connection.execute("BEGIN IMMEDIATE")
            rows = list(
                connection.execute(
                    """
                    SELECT event_id, body_bytes FROM outbox
                    WHERE state = ? AND body IS NOT NULL AND acknowledgement_json IS NOT NULL
                    ORDER BY created_order
                    """,
                    (ACKNOWLEDGED,),
                )
            )
            row_count = len(rows)
            byte_count = sum(row["body_bytes"] for row in rows)
            remove: list[str] = []
            for row in rows:
                if row_count <= max_payload_rows and byte_count <= max_payload_bytes:
                    break
                if not self._terminal_evidence_valid(connection, row["event_id"]):
                    raise OutboxError("cannot compact: terminal evidence is invalid")
                remove.append(row["event_id"])
                row_count -= 1
                byte_count -= row["body_bytes"]
            for event_id in remove:
                connection.execute("UPDATE outbox SET body = NULL WHERE event_id = ?", (event_id,))
                connection.execute(
                    "UPDATE source_events SET body = NULL WHERE event_id = ?", (event_id,)
                )
            connection.commit()
            return len(remove)
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def source_body(self, event_id: str) -> bytes | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT body FROM source_events WHERE event_id = ?", (event_id,)
            ).fetchone()
            return None if row is None or row["body"] is None else bytes(row["body"])
        finally:
            connection.close()

    def outbox_item(self, event_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute("SELECT * FROM outbox WHERE event_id = ?", (event_id,)).fetchone()
            if row is None:
                return None
            item = dict(row)
            item["body"] = None if item["body"] is None else bytes(item["body"])
            return item
        finally:
            connection.close()

    def receipt(self, event_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute("SELECT * FROM receipts WHERE event_id = ?", (event_id,)).fetchone()
            return None if row is None else dict(row)
        finally:
            connection.close()

    def status(self, event_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            source = connection.execute(
                "SELECT 1 FROM source_events WHERE event_id = ?", (event_id,)
            ).fetchone()
            outbox = connection.execute(
                "SELECT * FROM outbox WHERE event_id = ?", (event_id,)
            ).fetchone()
            if outbox is None:
                state = "conflict_recovery_required" if source is not None else "not_saved"
                return {"user_state": state, "event_id": event_id}
            if outbox["state"] == CONFLICT:
                return {"user_state": "conflict_recovery_required", "event_id": event_id}
            if outbox["state"] == ACKNOWLEDGED:
                state = (
                    "server_acknowledged"
                    if self._terminal_evidence_valid(connection, event_id)
                    else "conflict_recovery_required"
                )
                return {"user_state": state, "event_id": event_id}
            return {"user_state": "saved_on_device_and_queued", "event_id": event_id}
        finally:
            connection.close()

    @staticmethod
    def _record_conflict(
        connection: sqlite3.Connection,
        *,
        event_id: str,
        reason: str,
        accepted_digest: str,
        incoming_digest: str,
        incoming_body: bytes,
    ) -> None:
        details = json.dumps(
            {
                "event_id": event_id,
                "reason": reason,
                "accepted_body_sha256": accepted_digest,
                "incoming_sha256": incoming_digest,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        connection.execute(
            """
            INSERT INTO conflict_evidence (
                event_id, reason_code, accepted_body_sha256, incoming_sha256,
                incoming_body, details_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id, reason_code, incoming_sha256) DO NOTHING
            """,
            (event_id, reason, accepted_digest, incoming_digest, incoming_body, details),
        )
        connection.execute("UPDATE outbox SET state = ? WHERE event_id = ?", (CONFLICT, event_id))

    @staticmethod
    def _terminal_evidence_valid(connection: sqlite3.Connection, event_id: str) -> bool:
        row = connection.execute(
            """
            SELECT o.state, o.body AS outbox_body,
                   o.body_sha256 AS outbox_sha256, o.body_bytes AS outbox_bytes,
                   o.acknowledgement_json AS outbox_ack,
                   s.body AS source_body, s.body_sha256 AS source_sha256,
                   s.body_bytes AS source_bytes,
                   r.body_sha256 AS receipt_sha256, r.body_bytes AS receipt_bytes,
                   r.canonical_sequence, r.contract_version, r.acknowledgement_json AS receipt_ack
            FROM outbox o
            JOIN source_events s ON s.event_id = o.event_id
            LEFT JOIN receipts r ON r.event_id = o.event_id
            WHERE o.event_id = ?
            """,
            (event_id,),
        ).fetchone()
        if row is None or row["state"] != ACKNOWLEDGED or row["receipt_sha256"] is None:
            return False
        if (
            row["outbox_sha256"] != row["receipt_sha256"]
            or row["source_sha256"] != row["receipt_sha256"]
            or row["outbox_bytes"] != row["receipt_bytes"]
            or row["source_bytes"] != row["receipt_bytes"]
            or row["contract_version"] != CONTRACT_VERSION
            or row["canonical_sequence"] < 1
            or row["outbox_ack"] is None
            or bytes(row["outbox_ack"]) != bytes(row["receipt_ack"])
        ):
            return False
        outbox_body = None if row["outbox_body"] is None else bytes(row["outbox_body"])
        source_body = None if row["source_body"] is None else bytes(row["source_body"])
        if (outbox_body is None) != (source_body is None):
            return False
        if outbox_body is not None and (
            outbox_body != source_body
            or len(outbox_body) != row["receipt_bytes"]
            or hashlib.sha256(outbox_body).hexdigest() != row["receipt_sha256"]
        ):
            return False
        try:
            ack = json.loads(bytes(row["receipt_ack"]))
        except (json.JSONDecodeError, UnicodeError):
            return False
        return (
            ack.get("event_id") == event_id
            and ack.get("accepted_body_sha256") == row["receipt_sha256"]
            and ack.get("accepted_body_bytes") == row["receipt_bytes"]
            and ack.get("canonical_sequence") == row["canonical_sequence"]
            and ack.get("contract_version") == CONTRACT_VERSION
            and ack.get("status") == "accepted"
            and ack.get("ack_version") == ACK_VERSION
        )

    @staticmethod
    def _assert_no_orphans(connection: sqlite3.Connection, *, error_type: type[OutboxError]) -> None:
        source_without_outbox = connection.execute(
            "SELECT 1 FROM source_events s LEFT JOIN outbox o ON o.event_id=s.event_id WHERE o.event_id IS NULL LIMIT 1"
        ).fetchone()
        outbox_without_source = connection.execute(
            "SELECT 1 FROM outbox o LEFT JOIN source_events s ON s.event_id=o.event_id WHERE s.event_id IS NULL LIMIT 1"
        ).fetchone()
        if source_without_outbox or outbox_without_source:
            raise error_type("source/outbox invariant is broken")

    def conflict_count(self, event_id: str) -> int:
        connection = self._connect()
        try:
            return connection.execute(
                "SELECT COUNT(*) FROM conflict_evidence WHERE event_id = ?", (event_id,)
            ).fetchone()[0]
        finally:
            connection.close()

    def latest_conflict_body(self, event_id: str) -> bytes | None:
        connection = self._connect()
        try:
            row = connection.execute(
                """
                SELECT incoming_body FROM conflict_evidence
                WHERE event_id = ? ORDER BY conflict_id DESC LIMIT 1
                """,
                (event_id,),
            ).fetchone()
            return None if row is None else bytes(row["incoming_body"])
        finally:
            connection.close()

    def reset_conflict_for_retry(self, event_id: str) -> None:
        """Explicit test/reference recovery action; conflict evidence remains immutable."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM conflict_evidence WHERE event_id = ?", (event_id,)
            ).fetchone() is None:
                raise OutboxError("no durable conflict evidence exists")
            connection.execute(
                "UPDATE outbox SET state = ? WHERE event_id = ? AND state = ?",
                (PENDING, event_id, CONFLICT),
            )
            connection.commit()
        finally:
            connection.close()

    def counts(self) -> dict[str, int]:
        connection = self._connect()
        try:
            return {
                "sources": connection.execute("SELECT COUNT(*) FROM source_events").fetchone()[0],
                "outbox": connection.execute("SELECT COUNT(*) FROM outbox").fetchone()[0],
                "receipts": connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0],
            }
        finally:
            connection.close()

    def integrity_check(self) -> str:
        connection = self._connect()
        try:
            return connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()
