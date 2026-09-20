#!/usr/bin/env python3
"""Canonical immutable, byte-rehashed ingestion authority."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from mhpss_v2 import CONTRACT_VERSION, EnvelopeError, parse_envelope

ACK_VERSION = "mhpss.ack/2.0"
MAX_AUTHORITY_RECORD_BYTES = 524_288


class IngestIntegrityError(RuntimeError):
    """Canonical immutable authority failed rehash or semantic validation."""


class IngestStore:
    """Sole executable writer for canonical V2 immutable authority."""

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
                CREATE TABLE IF NOT EXISTS projection_cache (
                    stream_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    body_sha256 TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS rejection_log (
                    rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    body_sha256 TEXT NOT NULL,
                    error_code TEXT NOT NULL,
                    details_json BLOB NOT NULL,
                    UNIQUE(body_sha256, error_code)
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
            return self._record_rejection(
                body_sha256=digest,
                event_id=None,
                code="INVALID_ENVELOPE",
                message=str(error),
            )

        event_id = envelope["event_id"]
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            records = self._validated_records(connection)
            existing = self._event_record(records, event_id)
            if existing is not None:
                accepted_body = existing["event"]["body"]
                if accepted_body == body:
                    acknowledgement = self._acknowledgement(existing)
                    connection.rollback()
                    return {"outcome": "replayed", "acknowledgement": acknowledgement}
                if self._conflict_recorded(records, event_id, digest):
                    connection.rollback()
                    return {
                        "outcome": "conflict",
                        "error": {
                            "code": "EVENT_ID_BODY_CONFLICT",
                            "event_id": event_id,
                            "accepted_body_sha256": existing["event"]["body_sha256"],
                            "incoming_body_sha256": digest,
                        },
                    }
                self._append_record(
                    connection,
                    "canonical_conflict",
                    event_id,
                    {
                        "event_id": event_id,
                        "accepted_body_sha256": existing["event"]["body_sha256"],
                        "incoming_body_sha256": digest,
                        "incoming_body_b64": base64.b64encode(body).decode("ascii"),
                    },
                )
                connection.commit()
                return {
                    "outcome": "conflict",
                    "error": {
                        "code": "EVENT_ID_BODY_CONFLICT",
                        "event_id": event_id,
                        "accepted_body_sha256": existing["event"]["body_sha256"],
                        "incoming_body_sha256": digest,
                    },
                }

            lineage_error = self._lineage_error(records, envelope)
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

            self._append_record(
                connection,
                "canonical_event",
                event_id,
                self._event_value(body),
            )
            records = self._validated_records(connection)
            accepted = self._event_record(records, event_id)
            if accepted is None:
                raise IngestIntegrityError("accepted event is absent from immutable authority")
            self._refresh_projection_cache(connection, records)
            acknowledgement = self._acknowledgement(accepted)
            if crash_at == "before_commit":
                os._exit(97)
            connection.commit()
            if crash_at == "after_commit":
                os._exit(98)
            return {"outcome": "accepted", "acknowledgement": acknowledgement}
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def event_body(self, event_id: str) -> bytes | None:
        connection = self._connect()
        try:
            record = self._event_record(self._validated_records(connection), event_id)
            return None if record is None else record["event"]["body"]
        finally:
            connection.close()

    def projection(self, stream_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            records = self._validated_records(connection)
            latest = self._latest_events(records).get(stream_id)
            if latest is None:
                return None
            event = latest["event"]
            return {
                "stream_id": stream_id,
                "event_id": event["event_id"],
                "revision": event["revision"],
                "body_sha256": event["body_sha256"],
            }
        finally:
            connection.close()

    def lineage(self, stream_id: str) -> list[str]:
        connection = self._connect()
        try:
            records = self._validated_records(connection)
            events = [
                record["event"]
                for record in records
                if record["kind"] == "canonical_event"
                and record["event"]["stream_id"] == stream_id
            ]
            return [event["event_id"] for event in sorted(events, key=lambda item: item["revision"], reverse=True)]
        finally:
            connection.close()

    def dq_items(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            records = self._validated_records(connection)
            events = [record for record in records if record["kind"] == "canonical_event"]
            resolved = {
                record["value"]["dq_key"]: record["value"]["resolved_by_event_id"]
                for record in records
                if record["kind"] == "canonical_dq_resolution"
            }
            seen: dict[str, dict[str, Any]] = {}
            items: list[dict[str, Any]] = []
            for record in events:
                event = record["event"]
                fingerprint = event["duplicate_fingerprint"]
                if fingerprint is None:
                    continue
                prior = seen.get(fingerprint)
                if prior is not None and prior["stream_id"] != event["stream_id"]:
                    key = f"POSSIBLE_DUPLICATE|{event['event_id']}|{prior['event_id']}"
                    items.append(
                        {
                            "dq_id": len(items) + 1,
                            "dq_key": key,
                            "rule_code": "POSSIBLE_DUPLICATE",
                            "event_id": event["event_id"],
                            "related_event_id": prior["event_id"],
                            "status": "resolved" if key in resolved else "open",
                            "rule_version": "duplicate-fingerprint/2",
                            "evidence_digest": hashlib.sha256(key.encode()).hexdigest(),
                            "resolved_by_event_id": resolved.get(key),
                        }
                    )
                else:
                    seen[fingerprint] = event
            return items
        finally:
            connection.close()

    def resolve_dq(self, dq_id: int, correction_event_id: str) -> None:
        items = self.dq_items()
        item = next((candidate for candidate in items if candidate["dq_id"] == dq_id), None)
        if item is None:
            raise ValueError("DQ item does not exist")
        if item["status"] != "open":
            raise ValueError("DQ item is not open")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            records = self._validated_records(connection)
            correction = self._event_record(records, correction_event_id)
            if (
                correction is None
                or correction["event"]["event_type"] not in {"correction", "void"}
                or correction["event"]["predecessor_event_id"] != item["event_id"]
            ):
                raise ValueError("DQ resolution requires an accepted correction of the flagged event")
            self._append_record(
                connection,
                "canonical_dq_resolution",
                item["event_id"],
                {
                    "event_id": item["event_id"],
                    "dq_key": item["dq_key"],
                    "resolved_by_event_id": correction_event_id,
                },
            )
            self._validated_records(connection)
            connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def reconcile(self, *, client_receipts: list[dict[str, str]]) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            try:
                records = self._validated_records(connection)
            except IngestIntegrityError:
                differences = [{"code": "AUTHORITY_INTEGRITY_FAILURE", "event_id": ""}]
                return self._reconciliation_report(connection, [], differences)

            differences: list[dict[str, str]] = []
            events = {
                record["event"]["event_id"]: record
                for record in records
                if record["kind"] == "canonical_event"
            }
            normalized = sorted(
                [
                    {
                        "event_id": receipt.get("event_id", ""),
                        "body_sha256": receipt.get("body_sha256", ""),
                    }
                    for receipt in client_receipts
                ],
                key=lambda item: (item["event_id"], item["body_sha256"]),
            )
            grouped: dict[str, list[str]] = {}
            for receipt_value in normalized:
                grouped.setdefault(receipt_value["event_id"], []).append(receipt_value["body_sha256"])
            for event_id in sorted(grouped):
                digests = grouped[event_id]
                if len(digests) > 1:
                    differences.append({"code": "DUPLICATE_CLIENT_RECEIPT", "event_id": event_id})
                event = events.get(event_id)
                if event is None:
                    differences.append({"code": "CLIENT_EVENT_MISSING_CANONICAL", "event_id": event_id})
                elif any(digest != event["event"]["body_sha256"] for digest in digests):
                    differences.append({"code": "CLIENT_CANONICAL_DIGEST_MISMATCH", "event_id": event_id})
            for event_id in sorted(set(events) - set(grouped)):
                differences.append({"code": "CANONICAL_EVENT_MISSING_CLIENT_RECEIPT", "event_id": event_id})

            latest = self._latest_events(records)
            rows = list(connection.execute("SELECT * FROM projection_cache ORDER BY stream_id"))
            cache = {row["stream_id"]: row for row in rows}
            for stream_id, record in sorted(latest.items()):
                event = record["event"]
                row = cache.get(stream_id)
                if row is None or (
                    row["event_id"] != event["event_id"]
                    or row["revision"] != event["revision"]
                    or row["body_sha256"] != event["body_sha256"]
                ):
                    differences.append({"code": "STALE_OR_CORRUPT_PROJECTION", "event_id": event["event_id"]})
            for stream_id, row in sorted(cache.items()):
                target = events.get(row["event_id"])
                if stream_id not in latest or target is None or target["event"]["stream_id"] != stream_id:
                    differences.append({"code": "UNRELATED_PROJECTION", "event_id": row["event_id"]})
            differences.sort(key=lambda item: (item["code"], item["event_id"]))
            return self._reconciliation_report(connection, normalized, differences)
        finally:
            if connection.in_transaction:
                connection.rollback()
            connection.close()

    def counts(self) -> dict[str, int]:
        connection = self._connect()
        try:
            records = self._validated_records(connection)
            return {
                "events": sum(record["kind"] == "canonical_event" for record in records),
                "projections": len(self._latest_events(records)),
                "conflicts": sum(record["kind"] == "canonical_conflict" for record in records),
                "rejections": connection.execute("SELECT COUNT(*) FROM rejection_log").fetchone()[0],
                "dq_items": len(self.dq_items()),
            }
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
        details = IngestStore._canonical(error)
        connection.execute(
            """
            INSERT INTO rejection_log (event_id, body_sha256, error_code, details_json)
            VALUES (?, ?, ?, ?) ON CONFLICT(body_sha256, error_code) DO NOTHING
            """,
            (event_id, body_sha256, code, details),
        )
        return {"outcome": "rejected", "error": error}

    @classmethod
    def _validated_records(cls, connection: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = list(connection.execute("SELECT * FROM authority_records ORDER BY sequence"))
        records: list[dict[str, Any]] = []
        previous_hash: str | None = None
        streams: dict[str, dict[str, Any]] = {}
        event_ids: set[str] = set()
        conflicts: set[tuple[str, str]] = set()
        dq_keys: set[str] = set()
        for expected_sequence, row in enumerate(rows, start=1):
            data = bytes(row["data"])
            if row["sequence"] != expected_sequence or len(data) > MAX_AUTHORITY_RECORD_BYTES:
                raise IngestIntegrityError("canonical authority sequence or size bound is invalid")
            if row["previous_hash"] != previous_hash:
                raise IngestIntegrityError("canonical authority chain is broken")
            calculated = cls._record_digest(previous_hash, row["kind"], row["subject_id"], data)
            if row["record_hash"] != calculated:
                raise IngestIntegrityError("canonical authority record hash mismatch")
            try:
                value = cls._strict_json(data)
            except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as error:
                raise IngestIntegrityError("canonical authority JSON is invalid") from error
            if not isinstance(value, dict) or value.get("event_id") != row["subject_id"]:
                raise IngestIntegrityError("canonical authority subject is invalid")
            record: dict[str, Any] = {
                "sequence": row["sequence"],
                "kind": row["kind"],
                "subject_id": row["subject_id"],
                "record_hash": row["record_hash"],
                "value": value,
            }
            if row["kind"] == "canonical_event":
                event = cls._validate_event_value(value)
                if event["event_id"] in event_ids:
                    raise IngestIntegrityError("canonical event identity is duplicated")
                latest = streams.get(event["stream_id"])
                if event["event_type"] == "submission":
                    if latest is not None:
                        raise IngestIntegrityError("canonical stream has duplicate root")
                elif latest is None or (
                    event["revision"] != latest["revision"] + 1
                    or event["predecessor_event_id"] != latest["event_id"]
                    or event["schema_name"] != latest["schema_name"]
                ):
                    raise IngestIntegrityError("canonical event lineage has a fork or gap")
                streams[event["stream_id"]] = event
                event_ids.add(event["event_id"])
                record["event"] = event
            elif row["kind"] == "canonical_conflict":
                if row["subject_id"] not in event_ids:
                    raise IngestIntegrityError("canonical conflict lacks an accepted event")
                incoming = base64.b64decode(value["incoming_body_b64"], validate=True)
                if hashlib.sha256(incoming).hexdigest() != value["incoming_body_sha256"]:
                    raise IngestIntegrityError("canonical conflict bytes do not match their digest")
                key = (row["subject_id"], value["incoming_body_sha256"])
                if key in conflicts:
                    raise IngestIntegrityError("canonical conflict evidence is duplicated")
                conflicts.add(key)
            elif row["kind"] == "canonical_dq_resolution":
                if (
                    value.get("dq_key") in dq_keys
                    or value.get("resolved_by_event_id") not in event_ids
                    or row["subject_id"] not in event_ids
                ):
                    raise IngestIntegrityError("canonical DQ resolution is invalid")
                dq_keys.add(value["dq_key"])
            else:
                raise IngestIntegrityError(f"unknown canonical authority kind: {row['kind']}")
            records.append(record)
            previous_hash = calculated
        return records

    @staticmethod
    def _lineage_error(
        records: list[dict[str, Any]], envelope: dict[str, Any]
    ) -> str | None:
        latest = IngestStore._latest_events(records).get(envelope["stream_id"])
        if envelope["event_type"] == "submission":
            return None if latest is None else "submission stream already has a current event"
        if latest is None:
            return "successor stream has no accepted predecessor"
        event = latest["event"]
        if envelope["schema_name"] != event["schema_name"]:
            return "successor schema does not match predecessor schema"
        if envelope["revision"] != event["revision"] + 1:
            return "successor revision is not exactly current revision plus one"
        if envelope["predecessor_event_id"] != event["event_id"]:
            return "successor predecessor is not the current event"
        return None

    @classmethod
    def _event_value(cls, body: bytes) -> dict[str, Any]:
        envelope = parse_envelope(body)
        return {
            "event_id": envelope["event_id"],
            "body_b64": base64.b64encode(body).decode("ascii"),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "body_bytes": len(body),
        }

    @classmethod
    def _validate_event_value(cls, value: dict[str, Any]) -> dict[str, Any]:
        if set(value) != {"event_id", "body_b64", "body_sha256", "body_bytes"}:
            raise IngestIntegrityError("canonical event fields are incomplete or unknown")
        try:
            body = base64.b64decode(value["body_b64"], validate=True)
        except (ValueError, TypeError) as error:
            raise IngestIntegrityError("canonical event body encoding is invalid") from error
        if (
            hashlib.sha256(body).hexdigest() != value["body_sha256"]
            or len(body) != value["body_bytes"]
        ):
            raise IngestIntegrityError("canonical event body bytes do not match authority")
        try:
            envelope = parse_envelope(body)
        except EnvelopeError as error:
            raise IngestIntegrityError("canonical event body is not a valid envelope") from error
        if envelope["event_id"] != value["event_id"]:
            raise IngestIntegrityError("canonical event identity differs from exact body")
        return {
            **envelope,
            "body": body,
            "body_sha256": value["body_sha256"],
            "body_bytes": value["body_bytes"],
        }

    @staticmethod
    def _event_record(
        records: list[dict[str, Any]], event_id: str
    ) -> dict[str, Any] | None:
        return next(
            (
                record for record in records
                if record["kind"] == "canonical_event" and record["subject_id"] == event_id
            ),
            None,
        )

    @staticmethod
    def _conflict_recorded(
        records: list[dict[str, Any]], event_id: str, incoming_body_sha256: str
    ) -> bool:
        return any(
            record["kind"] == "canonical_conflict"
            and record["subject_id"] == event_id
            and record["value"].get("incoming_body_sha256") == incoming_body_sha256
            for record in records
        )

    @staticmethod
    def _latest_events(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for record in records:
            if record["kind"] == "canonical_event":
                latest[record["event"]["stream_id"]] = record
        return latest

    @staticmethod
    def _acknowledgement(record: dict[str, Any]) -> dict[str, Any]:
        event = record["event"]
        return {
            "ack_version": ACK_VERSION,
            "status": "accepted",
            "event_id": event["event_id"],
            "accepted_body_sha256": event["body_sha256"],
            "accepted_body_bytes": event["body_bytes"],
            "canonical_sequence": record["sequence"],
            "contract_version": CONTRACT_VERSION,
        }

    @classmethod
    def _refresh_projection_cache(
        cls, connection: sqlite3.Connection, records: list[dict[str, Any]]
    ) -> None:
        connection.execute("DELETE FROM projection_cache")
        for stream_id, record in cls._latest_events(records).items():
            event = record["event"]
            connection.execute(
                "INSERT INTO projection_cache VALUES (?, ?, ?, ?)",
                (stream_id, event["event_id"], event["revision"], event["body_sha256"]),
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
            raise IngestIntegrityError("canonical authority record exceeds its bound")
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
            raise ValueError("canonical authority JSON is not canonical")
        return value

    @staticmethod
    def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    @classmethod
    def _reconciliation_report(
        cls,
        connection: sqlite3.Connection,
        normalized_receipts: list[dict[str, str]],
        differences: list[dict[str, str]],
    ) -> dict[str, Any]:
        counts = {
            "events": connection.execute(
                "SELECT COUNT(*) FROM authority_records WHERE kind='canonical_event'"
            ).fetchone()[0],
            "projections": connection.execute("SELECT COUNT(*) FROM projection_cache").fetchone()[0],
            "conflicts": connection.execute(
                "SELECT COUNT(*) FROM authority_records WHERE kind='canonical_conflict'"
            ).fetchone()[0],
            "rejections": connection.execute("SELECT COUNT(*) FROM rejection_log").fetchone()[0],
        }
        evidence = cls._canonical(
            {
                "counts": counts,
                "client_receipts": normalized_receipts,
                "differences": differences,
            }
        )
        return {
            "contract": "mhpss.reconciliation/2.0",
            "clean": not differences,
            "counts": counts,
            "differences": differences,
            "evidence_sha256": hashlib.sha256(evidence).hexdigest(),
        }