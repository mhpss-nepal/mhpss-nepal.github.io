#!/usr/bin/env python3
"""Executable V2 envelope and identity contracts."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "contracts"))

from mhpss_v2 import (  # noqa: E402
    CONTRACT_VERSION,
    EnvelopeError,
    canonical_bytes,
    new_correction as _new_correction,
    new_legacy_import as _new_legacy_import,
    new_submission as _new_submission,
    parse_envelope,
    uuid7,
)
from release_contract import ReleaseManifest, verify_runtime_components  # noqa: E402


def new_submission(**values):
    values.pop("event_id", None)
    return _new_submission(**values)


def new_correction(**values):
    values.pop("event_id", None)
    return _new_correction(**values)


def new_legacy_import(**values):
    values.pop("event_id", None)
    return _new_legacy_import(**values)


def runtime_proof(release_id: str = "test-release-a"):
    bodies = {"/index.html": b"public", "/form/app.js": b"form", "/hub/app.js": b"hub"}
    manifest = ReleaseManifest.from_bodies(
        release_id=release_id,
        contract_version=CONTRACT_VERSION,
        cache_version="test-cache-a",
        bodies=bodies,
    )
    components = {
        name: {
            "release_id": release_id,
            "contract_version": CONTRACT_VERSION,
            "manifest_sha256": manifest.digest(),
        }
        for name in ("form", "hub", "contracts")
    }
    return verify_runtime_components(
        manifest=manifest,
        cached_bodies=bodies,
        components=components,
        trusted_manifest_sha256=manifest.digest(),
    )


def v1_rid(record: dict[str, str]) -> str:
    """Reproduce the frozen V1 FNV-1a content identity."""
    parts = (
        record.get("org", ""),
        record.get("orgOther", ""),
        record.get("site", ""),
        record.get("siteOther", ""),
        record.get("palika", ""),
        record.get("dateAD", ""),
        record.get("activity", ""),
        record.get("modality", ""),
        record.get("sessionTime", ""),
    )
    value = 0x811C9DC5
    for character in "|".join(parts):
        value ^= ord(character)
        value = (value * 0x01000193) & 0xFFFFFFFF
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    encoded = "0"
    if value:
        encoded = ""
        while value:
            value, remainder = divmod(value, 36)
            encoded = alphabet[remainder] + encoded
    return "R" + encoded.rjust(7, "0")


class EventIdentityTests(unittest.TestCase):
    def test_v1_collision_becomes_two_distinct_immutable_v2_events(self) -> None:
        common = {
            "org": "OTHER",
            "site": "FACILITY",
            "siteOther": "",
            "palika": "NP30001",
            "dateAD": "2026-09-19",
            "activity": "1.1",
            "modality": "IN_PERSON",
            "sessionTime": "09:00",
        }
        first = {**common, "orgOther": "COLLISION-1439599"}
        second = {**common, "orgOther": "COLLISION-1622382"}
        self.assertEqual(v1_rid(first), "R0Q7KEN4")
        self.assertEqual(v1_rid(first), v1_rid(second))

        first_event = new_submission(
            schema_name="synthetic.activity",
            payload=first,
            duplicate_fingerprint="sha256:shared-candidate",
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/1",
            release_id="test-release-a",
            runtime_proof=runtime_proof(),
            event_id=uuid7(now_ms=1_800_000_000_000, random_bits=1),
        )
        second_event = new_submission(
            schema_name="synthetic.activity",
            payload=second,
            duplicate_fingerprint="sha256:shared-candidate",
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/1",
            release_id="test-release-a",
            runtime_proof=runtime_proof(),
            event_id=uuid7(now_ms=1_800_000_000_000, random_bits=2),
        )

        self.assertNotEqual(first_event["event_id"], second_event["event_id"])
        self.assertEqual(first_event["stream_id"], first_event["event_id"])
        self.assertEqual(second_event["stream_id"], second_event["event_id"])
        self.assertEqual(first_event["duplicate_fingerprint"], second_event["duplicate_fingerprint"])

    def test_retry_serialization_is_byte_identical(self) -> None:
        event = new_submission(
            schema_name="synthetic.activity",
            payload={"count": 1, "label": "demo"},
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/1",
            release_id="test-release-a",
            runtime_proof=runtime_proof(),
            event_id=uuid7(now_ms=1_800_000_000_000, random_bits=3),
        )
        first = canonical_bytes(event)
        second = canonical_bytes(parse_envelope(first))
        self.assertEqual(first, second)

    def test_correction_gets_new_event_id_and_preserves_lineage(self) -> None:
        original = new_submission(
            schema_name="synthetic.activity",
            payload={"count": 1},
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/1",
            release_id="test-release-a",
            runtime_proof=runtime_proof(),
            event_id=uuid7(now_ms=1_800_000_000_000, random_bits=4),
        )
        correction = new_correction(
            predecessor=original,
            payload={"count": 2},
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:01:00Z",
            client_version="test-client/1",
            release_id="test-release-a",
            runtime_proof=runtime_proof(),
            event_id=uuid7(now_ms=1_800_000_000_001, random_bits=5),
        )
        self.assertNotEqual(correction["event_id"], original["event_id"])
        self.assertEqual(correction["stream_id"], original["stream_id"])
        self.assertEqual(correction["revision"], 2)
        self.assertEqual(correction["predecessor_event_id"], original["event_id"])
        self.assertEqual(original["payload"], {"count": 1})

    def test_legacy_import_preserves_source_identity_without_reusing_it_as_event_id(self) -> None:
        imported = new_legacy_import(
            schema_name="synthetic.activity",
            payload={"count": 1},
            legacy_id="R0Q7KEN4",
            source_dataset="synthetic-v1-fixture",
            source_row="row-0001",
            source_sha256="1" * 64,
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:00:00Z",
            client_version="migration-test/1",
            release_id="test-release-a",
            runtime_proof=runtime_proof(),
            event_id=uuid7(now_ms=1_800_000_000_000, random_bits=9),
        )
        self.assertNotEqual(imported["event_id"], "R0Q7KEN4")
        self.assertEqual(imported["provenance"]["legacy_id"], "R0Q7KEN4")
        self.assertEqual(imported["provenance"]["source_dataset"], "synthetic-v1-fixture")
        self.assertEqual(imported["provenance"]["source_row"], "row-0001")
        self.assertEqual(imported["provenance"]["source_sha256"], "1" * 64)


class EnvelopeValidationTests(unittest.TestCase):
    def test_contract_is_versioned_and_round_trips(self) -> None:
        event = new_submission(
            schema_name="synthetic.activity",
            payload={"answer": True},
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/1",
            release_id="test-release-a",
            runtime_proof=runtime_proof(),
            event_id=uuid7(now_ms=1_800_000_000_000, random_bits=6),
        )
        self.assertEqual(event["contract_version"], CONTRACT_VERSION)
        self.assertEqual(parse_envelope(canonical_bytes(event)), event)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        raw = b'{"contract_version":"mhpss.event/1.0","contract_version":"mhpss.event/1.0"}'
        with self.assertRaisesRegex(EnvelopeError, "duplicate JSON key"):
            parse_envelope(raw)

    def test_non_finite_numbers_are_rejected(self) -> None:
        event = new_submission(
            schema_name="synthetic.activity",
            payload={"count": 1},
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/1",
            release_id="test-release-a",
            runtime_proof=runtime_proof(),
            event_id=uuid7(now_ms=1_800_000_000_000, random_bits=7),
        )
        event["payload"]["bad"] = float("nan")
        with self.assertRaisesRegex(EnvelopeError, "finite"):
            canonical_bytes(event)

    def test_unknown_fields_and_unsupported_contract_versions_fail_closed(self) -> None:
        event = new_submission(
            schema_name="synthetic.activity",
            payload={"count": 1},
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/1",
            release_id="test-release-a",
            runtime_proof=runtime_proof(),
            event_id=uuid7(now_ms=1_800_000_000_000, random_bits=8),
        )
        with self.subTest("unknown field"):
            changed = {**event, "unexpected": "no"}
            with self.assertRaisesRegex(EnvelopeError, "unknown envelope fields"):
                canonical_bytes(changed)
        with self.subTest("unsupported version"):
            changed = {**event, "contract_version": "mhpss.event/3.0"}
            raw = json.dumps(changed, separators=(",", ":"), sort_keys=True).encode()
            with self.assertRaisesRegex(EnvelopeError, "unsupported contract_version"):
                parse_envelope(raw)

    def test_resource_malformed_json_and_non_rfc3339_timestamps_fail_closed(self) -> None:
        with self.assertRaisesRegex(EnvelopeError, "integer|JSON"):
            parse_envelope(b'{"number":' + b"9" * 5000 + b"}")
        with self.assertRaisesRegex(EnvelopeError, "depth|JSON"):
            parse_envelope(b"[" * 1500 + b"0" + b"]" * 1500)

        for occurred_at in (
            "20260919T000000Z",
            "2026-09-19 00:00:00Z",
            "2026-W38-6T00:00:00Z",
        ):
            with self.subTest(occurred_at=occurred_at):
                with self.assertRaisesRegex(EnvelopeError, "RFC 3339"):
                    new_submission(
                        schema_name="synthetic.activity",
                        payload={"count": 1},
                        duplicate_fingerprint=None,
                        occurred_at=occurred_at,
                        client_version="test-client/1",
                        release_id="test-release-a",
                        runtime_proof=runtime_proof(),
                        event_id=uuid7(now_ms=1_800_000_000_000, random_bits=10),
                    )

    def test_event_creation_requires_a_matching_verified_runtime(self) -> None:
        with self.assertRaises((EnvelopeError, TypeError)):
            new_submission(
                schema_name="synthetic.activity",
                payload={"count": 1},
                duplicate_fingerprint=None,
                occurred_at="2026-09-19T00:00:00Z",
                client_version="test-client/1",
                release_id="test-release-a",
                runtime_proof=None,
                event_id=uuid7(now_ms=1_800_000_000_000, random_bits=11),
            )
        with self.assertRaises(EnvelopeError):
            new_submission(
                schema_name="synthetic.activity",
                payload={"count": 1},
                duplicate_fingerprint=None,
                occurred_at="2026-09-19T00:00:00Z",
                client_version="test-client/1",
                release_id="test-release-b",
                runtime_proof=runtime_proof("test-release-a"),
                event_id=uuid7(now_ms=1_800_000_000_000, random_bits=12),
            )


if __name__ == "__main__":
    unittest.main()
