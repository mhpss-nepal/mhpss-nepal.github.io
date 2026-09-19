#!/usr/bin/env python3
"""SQLite reference ingestion boundary for immutable V2 events."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from mhpss_v2 import CONTRACT_VERSION, EnvelopeError, parse_envelope

ACK_VERSION = "mhpss.ack/1.0"


class IngestStore:
    """Sole executable writer for canonical V2 reference events."""

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
                CREATE TABLE IF NOT EXISTS events (
                    canonical_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    stream_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    predecessor_event_id TEXT,
                    event_type TEXT NOT NULL,
                    body BLOB NOT NULL,
                    body_sha256 TEXT NOT NULL,
                    body_bytes INTEGER NOT NULL,
                    duplicate_fingerprint TEXT,
                    UNIQUE(stream_id, revision),
                    FOREIGN KEY(predecessor_event_id) REFERENCES events(event_id)
                );
                CREATE TABLE IF NOT EXISTS acknowledgements (
                    event_id TEXT PRIMARY KEY REFERENCES events(event_id),
                    body_sha256 TEXT NOT NULL,
                    acknowledgement_json BLOB NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projections (
                    stream_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE REFERENCES events(event_id),
                    revision INTEGER NOT NULL,
                    body_sha256 TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conflicts (
                    conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    accepted_body_sha256 TEXT NOT NULL,
                    incoming_body_sha256 TEXT NOT NULL,
                    incoming_body BLOB NOT NULL,
                    UNIQUE(event_id, incoming_body_sha256)
                );
                CREATE TABLE IF NOT EXISTS rejections (
                    rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    body_sha256 TEXT NOT NULL,
                    error_code TEXT NOT NULL,
                    details_json BLOB NOT NULL,
                    UNIQUE(body_sha256, error_code)
                );
                CREATE TABLE IF NOT EXISTS dq_items (
                    dq_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_code TEXT NOT NULL,
                    event_id TEXT NOT NULL REFERENCES events(event_id),
                    related_event_id TEXT REFERENCES events(event_id),
                    status TEXT NOT NULL,
                    rule_version TEXT NOT NULL,
                    evidence_digest TEXT NOT NULL,
                    resolved_by_event_id TEXT REFERENCES events(event_id),
                    UNIQUE(rule_code, event_id, related_event_id)
                );
                """
            )
        finally:
            connection.close()

    def ingest(self, body: bytes, *, crash_at: str | None = None) -> dict[str, Any]:
        digest = hashlib.sha256(body).hexdigest()
        try:
            envelope = parse_envelope(body)
        except EnvelopeError as error:
            result = self._record_rejection(
                body_sha256=digest,
                event_id=None,
                code="INVALID_ENVELOPE",
                message=str(error),
            )
            return result

        event_id = envelope["event_id"]
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT body, body_sha256 FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
            if existing is not None:
                if existing["body_sha256"] == digest and bytes(existing["body"]) == body:
                    acknowledgement = self._acknowledgement(connection, event_id)
                    connection.rollback()
                    return {"outcome": "replayed", "acknowledgement": acknowledgement}
                connection.execute(
                    """
                    INSERT INTO conflicts (
                        event_id, accepted_body_sha256, incoming_body_sha256, incoming_body
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(event_id, incoming_body_sha256) DO NOTHING
                    """,
                    (event_id, existing["body_sha256"], digest, body),
                )
                connection.commit()
                return {
                    "outcome": "conflict",
                    "error": {
                        "code": "EVENT_ID_BODY_CONFLICT",
                        "event_id": event_id,
                        "accepted_body_sha256": existing["body_sha256"],
                        "incoming_body_sha256": digest,
                    },
                }

            lineage_error = self._lineage_error(connection, envelope)
            if lineage_error is not None:
                result = self._insert_rejection(
                    connection,
                    body_sha256=digest,
                    event_id=event_id,
                    code="STALE_OR_GAPPED_REVISION",
                    message=lineage_error,
                )
                connection.commit()
                return result

            cursor = connection.execute(
                """
                INSERT INTO events (
                    event_id, stream_id, revision, predecessor_event_id, event_type,
                    body, body_sha256, body_bytes, duplicate_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    envelope["stream_id"],
                    envelope["revision"],
                    envelope["predecessor_event_id"],
                    envelope["event_type"],
                    body,
                    digest,
                    len(body),
                    envelope["duplicate_fingerprint"],
                ),
            )
            sequence = cursor.lastrowid
            if sequence is None:
                raise RuntimeError("accepted event did not receive a canonical sequence")
            connection.execute(
                """
                INSERT INTO projections (stream_id, event_id, revision, body_sha256)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(stream_id) DO UPDATE SET
                    event_id=excluded.event_id,
                    revision=excluded.revision,
                    body_sha256=excluded.body_sha256
                """,
                (envelope["stream_id"], event_id, envelope["revision"], digest),
            )
            acknowledgement = self._make_ack(event_id, digest, len(body), sequence)
            acknowledgement_bytes = json.dumps(
                acknowledgement, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            connection.execute(
                "INSERT INTO acknowledgements VALUES (?, ?, ?)",
                (event_id, digest, acknowledgement_bytes),
            )
            self._open_duplicate_dq(connection, envelope, digest)
            if crash_at == "before_commit":
                os._exit(93)
            connection.commit()
            if crash_at == "after_commit":
                os._exit(94)
            return {"outcome": "accepted", "acknowledgement": acknowledgement}
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _lineage_error(connection: sqlite3.Connection, envelope: dict[str, Any]) -> str | None:
        projection = connection.execute(
            "SELECT event_id, revision FROM projections WHERE stream_id = ?",
            (envelope["stream_id"],),
        ).fetchone()
        if envelope["event_type"] == "submission":
            if projection is not None:
                return "submission stream already has a current event"
            return None
        if projection is None:
            return "successor stream has no accepted predecessor"
        predecessor = connection.execute(
            "SELECT stream_id, body FROM events WHERE event_id = ?",
            (envelope["predecessor_event_id"],),
        ).fetchone()
        if predecessor is None:
            return "successor predecessor is not accepted"
        if predecessor["stream_id"] != envelope["stream_id"]:
            return "successor stream does not match predecessor stream"
        predecessor_envelope = json.loads(bytes(predecessor["body"]))
        if predecessor_envelope["schema_name"] != envelope["schema_name"]:
            return "successor schema does not match predecessor schema"
        if envelope["revision"] != projection["revision"] + 1:
            return "successor revision is not exactly current revision plus one"
        if envelope["predecessor_event_id"] != projection["event_id"]:
            return "successor predecessor is not the current event"
        return None

    def _record_rejection(
        self, *, body_sha256: str, event_id: str | None, code: str, message: str
    ) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            result = self._insert_rejection(
                connection,
                body_sha256=body_sha256,
                event_id=event_id,
                code=code,
                message=message,
            )
            connection.commit()
            return result
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _insert_rejection(
        connection: sqlite3.Connection,
        *,
        body_sha256: str,
        event_id: str | None,
        code: str,
        message: str,
    ) -> dict[str, Any]:
        error = {"code": code, "event_id": event_id, "message": message}
        details = json.dumps(error, separators=(",", ":"), sort_keys=True).encode("utf-8")
        connection.execute(
            """
            INSERT INTO rejections (event_id, body_sha256, error_code, details_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(body_sha256, error_code) DO NOTHING
            """,
            (event_id, body_sha256, code, details),
        )
        return {"outcome": "rejected", "error": error}

    @staticmethod
    def _make_ack(
        event_id: str, body_sha256: str, body_bytes: int, sequence: int
    ) -> dict[str, Any]:
        return {
            "ack_version": ACK_VERSION,
            "status": "accepted",
            "event_id": event_id,
            "accepted_body_sha256": body_sha256,
            "accepted_body_bytes": body_bytes,
            "canonical_sequence": sequence,
            "contract_version": CONTRACT_VERSION,
        }

    @staticmethod
    def _acknowledgement(connection: sqlite3.Connection, event_id: str) -> dict[str, Any]:
        row = connection.execute(
            "SELECT acknowledgement_json FROM acknowledgements WHERE event_id = ?", (event_id,)
        ).fetchone()
        if row is None:
            raise RuntimeError("accepted event is missing its atomic acknowledgement")
        return json.loads(bytes(row["acknowledgement_json"]))

    @staticmethod
    def _open_duplicate_dq(
        connection: sqlite3.Connection, envelope: dict[str, Any], body_sha256: str
    ) -> None:
        fingerprint = envelope["duplicate_fingerprint"]
        if fingerprint is None:
            return
        prior = connection.execute(
            """
            SELECT event_id, stream_id FROM events
            WHERE duplicate_fingerprint = ? AND event_id != ?
            ORDER BY canonical_sequence LIMIT 1
            """,
            (fingerprint, envelope["event_id"]),
        ).fetchone()
        if prior is None or prior["stream_id"] == envelope["stream_id"]:
            return
        evidence = hashlib.sha256(
            f"duplicate-fingerprint/1|{fingerprint}|{prior['event_id']}|{envelope['event_id']}|{body_sha256}".encode()
        ).hexdigest()
        connection.execute(
            """
            INSERT INTO dq_items (
                rule_code, event_id, related_event_id, status,
                rule_version, evidence_digest, resolved_by_event_id
            ) VALUES ('POSSIBLE_DUPLICATE', ?, ?, 'open', 'duplicate-fingerprint/1', ?, NULL)
            ON CONFLICT(rule_code, event_id, related_event_id) DO NOTHING
            """,
            (envelope["event_id"], prior["event_id"], evidence),
        )

    def event_body(self, event_id: str) -> bytes | None:
        connection = self._connect()
        try:
            row = connection.execute("SELECT body FROM events WHERE event_id = ?", (event_id,)).fetchone()
            return None if row is None else bytes(row["body"])
        finally:
            connection.close()

    def projection(self, stream_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM projections WHERE stream_id = ?", (stream_id,)
            ).fetchone()
            return None if row is None else dict(row)
        finally:
            connection.close()

    def lineage(self, stream_id: str) -> list[str]:
        connection = self._connect()
        try:
            return [
                row["event_id"]
                for row in connection.execute(
                    "SELECT event_id FROM events WHERE stream_id = ? ORDER BY revision DESC",
                    (stream_id,),
                )
            ]
        finally:
            connection.close()

    def dq_items(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute("SELECT * FROM dq_items ORDER BY dq_id")]
        finally:
            connection.close()

    def resolve_dq(self, dq_id: int, correction_event_id: str) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            item = connection.execute(
                "SELECT event_id, status FROM dq_items WHERE dq_id = ?", (dq_id,)
            ).fetchone()
            if item is None:
                raise ValueError("DQ item does not exist")
            if item["status"] != "open":
                raise ValueError("DQ item is not open")
            correction = connection.execute(
                """
                SELECT event_id, predecessor_event_id, event_type
                FROM events WHERE event_id = ?
                """,
                (correction_event_id,),
            ).fetchone()
            if (
                correction is None
                or correction["event_type"] not in {"correction", "void"}
                or correction["predecessor_event_id"] != item["event_id"]
            ):
                raise ValueError("DQ resolution requires an accepted correction of the flagged event")
            connection.execute(
                """
                UPDATE dq_items
                SET status = 'resolved', resolved_by_event_id = ?
                WHERE dq_id = ?
                """,
                (correction_event_id, dq_id),
            )
            connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def counts(self) -> dict[str, int]:
        connection = self._connect()
        try:
            return {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("events", "projections", "conflicts", "rejections", "dq_items")
            }
        finally:
            connection.close()

    def reconcile(self, *, client_receipts: list[dict[str, str]]) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            differences: list[dict[str, str]] = []
            normalized_receipts: list[dict[str, str]] = []
            seen: set[str] = set()
            for receipt in sorted(client_receipts, key=lambda item: item.get("event_id", "")):
                event_id = receipt.get("event_id", "")
                digest = receipt.get("body_sha256", "")
                normalized_receipts.append({"event_id": event_id, "body_sha256": digest})
                if event_id in seen:
                    differences.append({"code": "DUPLICATE_CLIENT_RECEIPT", "event_id": event_id})
                    continue
                seen.add(event_id)
                row = connection.execute(
                    "SELECT body_sha256 FROM events WHERE event_id = ?", (event_id,)
                ).fetchone()
                if row is None:
                    differences.append({"code": "CLIENT_EVENT_MISSING_CANONICAL", "event_id": event_id})
                elif row["body_sha256"] != digest:
                    differences.append(
                        {"code": "CLIENT_CANONICAL_DIGEST_MISMATCH", "event_id": event_id}
                    )
            for row in connection.execute("SELECT event_id FROM events ORDER BY event_id"):
                if row["event_id"] not in seen:
                    differences.append(
                        {
                            "code": "CANONICAL_EVENT_MISSING_CLIENT_RECEIPT",
                            "event_id": row["event_id"],
                        }
                    )
            projection_defects = connection.execute(
                """
                WITH latest AS (
                    SELECT stream_id, MAX(revision) AS revision
                    FROM events GROUP BY stream_id
                )
                SELECT e.event_id
                FROM latest l
                JOIN events e ON e.stream_id=l.stream_id AND e.revision=l.revision
                LEFT JOIN projections p ON p.stream_id=l.stream_id
                WHERE p.event_id IS NULL
                   OR p.event_id != e.event_id
                   OR p.revision != e.revision
                   OR p.body_sha256 != e.body_sha256
                ORDER BY e.event_id
                """
            ).fetchall()
            differences.extend(
                {"code": "STALE_OR_CORRUPT_PROJECTION", "event_id": row["event_id"]}
                for row in projection_defects
            )
            orphan_projections = connection.execute(
                """
                SELECT p.event_id FROM projections p
                LEFT JOIN events e ON e.event_id = p.event_id
                WHERE e.event_id IS NULL ORDER BY p.event_id
                """
            ).fetchall()
            differences.extend(
                {"code": "ORPHAN_PROJECTION", "event_id": row["event_id"]}
                for row in orphan_projections
            )
            counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("events", "projections", "conflicts", "rejections", "dq_items")
            }
            evidence = json.dumps(
                {
                    "counts": counts,
                    "client_receipts": normalized_receipts,
                    "differences": differences,
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            connection.rollback()
            return {
                "contract": "mhpss.reconciliation/1.0",
                "clean": not differences,
                "counts": counts,
                "differences": differences,
                "evidence_sha256": hashlib.sha256(evidence).hexdigest(),
            }
        finally:
            if connection.in_transaction:
                connection.rollback()
            connection.close()

    def integrity_check(self) -> str:
        connection = self._connect()
        try:
            return connection.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            connection.close()
