#!/usr/bin/env python3
"""MHPSS Nepal V2 immutable event envelope reference contract.

This module is a local executable specification. It is not a production runtime
and contains no network, Firebase, or deployment integration.
"""

from __future__ import annotations

import json
import math
import re
import secrets
import time
import uuid
from datetime import datetime
from typing import Any

from release_contract import RuntimeProof

CONTRACT_VERSION = "mhpss.event/1.0"
MAX_ENVELOPE_BYTES = 262_144
MAX_JSON_DEPTH = 12
MAX_JSON_NODES = 4_096

_REQUIRED_FIELDS = frozenset(
    {
        "contract_version",
        "schema_name",
        "event_id",
        "event_type",
        "stream_id",
        "revision",
        "predecessor_event_id",
        "occurred_at",
        "client_version",
        "release_id",
        "duplicate_fingerprint",
        "payload",
        "provenance",
    }
)
_EVENT_TYPES = frozenset({"submission", "correction", "void"})


class EnvelopeError(ValueError):
    """An envelope is malformed or incompatible with this contract."""


def uuid7(*, now_ms: int | None = None, random_bits: int | None = None) -> str:
    """Return a canonical UUIDv7 using the system CSPRNG by default."""
    timestamp = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    randomness = secrets.randbits(74) if random_bits is None else random_bits
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or not 0 <= timestamp < 2**48:
        raise ValueError("UUIDv7 timestamp must be a 48-bit non-negative integer")
    if isinstance(randomness, bool) or not isinstance(randomness, int) or not 0 <= randomness < 2**74:
        raise ValueError("UUIDv7 randomness must be a 74-bit non-negative integer")
    rand_a = randomness >> 62
    rand_b = randomness & ((1 << 62) - 1)
    value = (timestamp << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return str(uuid.UUID(int=value))


def new_submission(
    *,
    schema_name: str,
    payload: dict[str, Any],
    duplicate_fingerprint: str | None,
    occurred_at: str,
    client_version: str,
    release_id: str,
    runtime_proof: RuntimeProof,
    event_id: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one new immutable stream at revision one."""
    _runtime_matches(runtime_proof, release_id)
    identity = event_id or uuid7()
    envelope = {
        "contract_version": CONTRACT_VERSION,
        "schema_name": schema_name,
        "event_id": identity,
        "event_type": "submission",
        "stream_id": identity,
        "revision": 1,
        "predecessor_event_id": None,
        "occurred_at": occurred_at,
        "client_version": client_version,
        "release_id": release_id,
        "duplicate_fingerprint": duplicate_fingerprint,
        "payload": payload,
        "provenance": {} if provenance is None else provenance,
    }
    validate_envelope(envelope)
    return envelope


def new_correction(
    *,
    predecessor: dict[str, Any],
    payload: dict[str, Any],
    duplicate_fingerprint: str | None,
    occurred_at: str,
    client_version: str,
    release_id: str,
    runtime_proof: RuntimeProof,
    event_id: str | None = None,
    provenance: dict[str, Any] | None = None,
    event_type: str = "correction",
) -> dict[str, Any]:
    """Create an immutable correction or void linked to its predecessor."""
    validate_envelope(predecessor)
    _runtime_matches(runtime_proof, release_id)
    if event_type not in {"correction", "void"}:
        raise EnvelopeError("a successor event_type must be correction or void")
    envelope = {
        "contract_version": CONTRACT_VERSION,
        "schema_name": predecessor["schema_name"],
        "event_id": event_id or uuid7(),
        "event_type": event_type,
        "stream_id": predecessor["stream_id"],
        "revision": predecessor["revision"] + 1,
        "predecessor_event_id": predecessor["event_id"],
        "occurred_at": occurred_at,
        "client_version": client_version,
        "release_id": release_id,
        "duplicate_fingerprint": duplicate_fingerprint,
        "payload": payload,
        "provenance": {} if provenance is None else provenance,
    }
    validate_envelope(envelope)
    return envelope


def new_legacy_import(
    *,
    schema_name: str,
    payload: dict[str, Any],
    legacy_id: str,
    source_dataset: str,
    source_row: str,
    source_sha256: str,
    duplicate_fingerprint: str | None,
    occurred_at: str,
    client_version: str,
    release_id: str,
    runtime_proof: RuntimeProof,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Create a V2 event while retaining, but never trusting, V1 identity."""
    for value, label in (
        (legacy_id, "legacy_id"),
        (source_dataset, "source_dataset"),
        (source_row, "source_row"),
    ):
        _bounded_string(value, label, 256)
    if (
        not isinstance(source_sha256, str)
        or len(source_sha256) != 64
        or any(character not in "0123456789abcdef" for character in source_sha256)
    ):
        raise EnvelopeError("source_sha256 must be a lowercase SHA-256 digest")
    return new_submission(
        schema_name=schema_name,
        payload=payload,
        duplicate_fingerprint=duplicate_fingerprint,
        occurred_at=occurred_at,
        client_version=client_version,
        release_id=release_id,
        runtime_proof=runtime_proof,
        event_id=event_id,
        provenance={
            "kind": "legacy_import",
            "legacy_id": legacy_id,
            "source_dataset": source_dataset,
            "source_row": source_row,
            "source_sha256": source_sha256,
        },
    )


def canonical_bytes(envelope: dict[str, Any]) -> bytes:
    """Validate and serialize one envelope to stable UTF-8 JSON bytes."""
    validate_envelope(envelope)
    try:
        encoded = json.dumps(
            envelope,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise EnvelopeError(f"envelope is not finite JSON: {error}") from error
    if len(encoded) > MAX_ENVELOPE_BYTES:
        raise EnvelopeError("envelope exceeds the executable reference byte limit")
    return encoded


def parse_envelope(raw: bytes) -> dict[str, Any]:
    """Strictly parse and validate exact UTF-8 envelope bytes."""
    if not isinstance(raw, bytes):
        raise EnvelopeError("envelope input must be bytes")
    if len(raw) > MAX_ENVELOPE_BYTES:
        raise EnvelopeError("envelope exceeds the executable reference byte limit")
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise EnvelopeError("envelope is not valid UTF-8") from error
    try:
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except EnvelopeError:
        raise
    except (json.JSONDecodeError, UnicodeError, ValueError, RecursionError) as error:
        raise EnvelopeError(f"envelope is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise EnvelopeError("envelope root must be an object")
    validate_envelope(value)
    if canonical_bytes(value) != raw:
        raise EnvelopeError("envelope bytes are not in canonical JSON form")
    return value


def validate_envelope(envelope: dict[str, Any]) -> None:
    """Validate fields, identity, lineage, bounds, and JSON safety."""
    if not isinstance(envelope, dict):
        raise EnvelopeError("envelope must be an object")
    supplied = frozenset(envelope)
    missing = sorted(_REQUIRED_FIELDS - supplied)
    unknown = sorted(supplied - _REQUIRED_FIELDS)
    if missing:
        raise EnvelopeError(f"missing envelope fields: {', '.join(missing)}")
    if unknown:
        raise EnvelopeError(f"unknown envelope fields: {', '.join(unknown)}")
    if envelope["contract_version"] != CONTRACT_VERSION:
        raise EnvelopeError(f"unsupported contract_version: {envelope['contract_version']!r}")

    _bounded_string(envelope["schema_name"], "schema_name", 128)
    _uuid7_string(envelope["event_id"], "event_id")
    _uuid7_string(envelope["stream_id"], "stream_id")
    event_type = envelope["event_type"]
    if event_type not in _EVENT_TYPES:
        raise EnvelopeError(f"unsupported event_type: {event_type!r}")
    revision = envelope["revision"]
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise EnvelopeError("revision must be a positive integer")

    predecessor = envelope["predecessor_event_id"]
    if event_type == "submission":
        if revision != 1 or predecessor is not None:
            raise EnvelopeError("submission must be revision 1 without a predecessor")
        if envelope["stream_id"] != envelope["event_id"]:
            raise EnvelopeError("a new submission stream_id must equal its event_id")
    else:
        if revision < 2 or predecessor is None:
            raise EnvelopeError("a successor must have revision >= 2 and a predecessor")
        _uuid7_string(predecessor, "predecessor_event_id")
        if predecessor == envelope["event_id"]:
            raise EnvelopeError("an event cannot be its own predecessor")

    _rfc3339_utc(envelope["occurred_at"])
    _bounded_string(envelope["client_version"], "client_version", 128)
    _bounded_string(envelope["release_id"], "release_id", 128)
    fingerprint = envelope["duplicate_fingerprint"]
    if fingerprint is not None:
        _bounded_string(fingerprint, "duplicate_fingerprint", 160)
    if not isinstance(envelope["payload"], dict):
        raise EnvelopeError("payload must be an object")
    if not isinstance(envelope["provenance"], dict):
        raise EnvelopeError("provenance must be an object")
    _walk_json(envelope)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EnvelopeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise EnvelopeError(f"JSON numbers must be finite: {value}")


def _bounded_string(value: Any, field: str, maximum: int) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise EnvelopeError(f"{field} must be a non-empty string of at most {maximum} characters")
    if any(ord(character) < 0x20 for character in value):
        raise EnvelopeError(f"{field} contains a control character")


def _uuid7_string(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise EnvelopeError(f"{field} must be a canonical UUIDv7 string")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as error:
        raise EnvelopeError(f"{field} must be a canonical UUIDv7 string") from error
    if str(parsed) != value or parsed.version != 7 or parsed.variant != uuid.RFC_4122:
        raise EnvelopeError(f"{field} must be a canonical UUIDv7 string")


def _rfc3339_utc(value: Any) -> None:
    _bounded_string(value, "occurred_at", 32)
    if re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z", value
    ) is None:
        raise EnvelopeError("occurred_at must be RFC 3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise EnvelopeError("occurred_at must be RFC 3339 UTC ending in Z") from error
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise EnvelopeError("occurred_at must be UTC")


def _runtime_matches(runtime_proof: RuntimeProof, release_id: str) -> None:
    if not isinstance(runtime_proof, RuntimeProof):
        raise EnvelopeError("event creation requires verified runtime components")
    if runtime_proof.contract_version != CONTRACT_VERSION:
        raise EnvelopeError("runtime contract_version does not match event contract")
    if runtime_proof.release_id != release_id:
        raise EnvelopeError("runtime release_id does not match event release_id")


def _walk_json(root: Any) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(root, 1)]
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise EnvelopeError("envelope exceeds the executable reference JSON node limit")
        if depth > MAX_JSON_DEPTH:
            raise EnvelopeError("envelope exceeds the executable reference JSON depth limit")
        if value is None or isinstance(value, (str, bool)):
            continue
        if isinstance(value, int):
            continue
        if isinstance(value, float):
            if not math.isfinite(value):
                raise EnvelopeError("JSON numbers must be finite")
            continue
        if isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
            continue
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise EnvelopeError("JSON object keys must be strings")
                stack.append((item, depth + 1))
            continue
        raise EnvelopeError(f"unsupported JSON value type: {type(value).__name__}")
