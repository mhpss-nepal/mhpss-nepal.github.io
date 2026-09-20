#!/usr/bin/env python3
"""Regression contracts for the immutable-authority redesign."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "packages" / "contracts"
sys.path.insert(0, str(CONTRACTS))

import release_contract  # noqa: E402
from mhpss_v2 import EnvelopeError, new_submission  # noqa: E402
from release_contract import (  # noqa: E402
    MixedReleaseError,
    ReleaseManifest,
    verify_runtime_components,
)


def verified_runtime(*, bodies: dict[str, bytes] | None = None):
    cached = bodies or {
        "/index.html": b"public",
        "/form/app.js": b"form",
        "/hub/app.js": b"hub",
    }
    manifest = ReleaseManifest.from_bodies(
        release_id="test-release-a",
        contract_version="mhpss.event/2.0",
        cache_version="test-cache-a",
        bodies=cached,
    )
    components = {
        name: {
            "release_id": manifest.release_id,
            "contract_version": manifest.contract_version,
            "manifest_sha256": manifest.digest(),
        }
        for name in ("form", "hub", "contracts")
    }
    proof = verify_runtime_components(
        manifest=manifest,
        cached_bodies=cached,
        components=components,
        trusted_manifest_sha256=manifest.digest(),
    )
    return manifest, proof


class TrustedReleaseAndIdentityTests(unittest.TestCase):
    def test_public_submission_allocates_identity_and_proof_is_manifest_bound(self) -> None:
        manifest, proof = verified_runtime()
        event = new_submission(
            schema_name="synthetic.activity",
            payload={"count": 1},
            duplicate_fingerprint=None,
            occurred_at="2026-09-19T00:00:00Z",
            client_version="test-client/1",
            release_id=manifest.release_id,
            runtime_proof=proof,
        )
        self.assertEqual(event["stream_id"], event["event_id"])
        self.assertEqual(event["release_manifest_sha256"], manifest.digest())

        with self.assertRaises(TypeError):
            new_submission(
                schema_name="synthetic.activity",
                payload={"count": 2},
                duplicate_fingerprint=None,
                occurred_at="2026-09-19T00:00:00Z",
                client_version="test-client/1",
                release_id=manifest.release_id,
                runtime_proof=proof,
                event_id=event["event_id"],
            )
        with self.assertRaises(AttributeError):
            getattr(release_contract, "RuntimeProof")
        with self.assertRaises(AttributeError):
            getattr(release_contract, "_VerifiedRuntime")
        with self.assertRaises(AttributeError):
            getattr(release_contract, "_PROOF_SEAL")
        with self.assertRaises(AttributeError):
            getattr(release_contract, "_issue_runtime_proof")
        with self.assertRaises(TypeError):
            proof.__class__(
                proof.release_id,
                proof.contract_version,
                proof.manifest_sha256,
            )

        other_bodies = {
            "/index.html": b"public-v2",
            "/form/app.js": b"form-v2",
            "/hub/app.js": b"hub-v2",
        }
        other_manifest = ReleaseManifest.from_bodies(
            release_id=manifest.release_id,
            contract_version=manifest.contract_version,
            cache_version="test-cache-b",
            bodies=other_bodies,
        )
        other_components = {
            name: {
                "release_id": other_manifest.release_id,
                "contract_version": other_manifest.contract_version,
                "manifest_sha256": other_manifest.digest(),
            }
            for name in ("form", "hub", "contracts")
        }
        with self.assertRaises(MixedReleaseError):
            verify_runtime_components(
                manifest=other_manifest,
                cached_bodies=other_bodies,
                components=other_components,
                trusted_manifest_sha256=manifest.digest(),
            )

    def test_release_paths_are_canonical_and_collision_free(self) -> None:
        invalid_paths = (
            "/../secret",
            "/a/../b",
            "//double",
            "/line\nbreak",
            "/encoded%2e%2e/secret",
            "/back\\slash",
            "/trailing./file",
            "/CON/file",
            "/a/./b",
        )
        for path in invalid_paths:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    ReleaseManifest.from_bodies(
                        release_id="test-release-a",
                        contract_version="mhpss.event/2.0",
                        cache_version="test-cache-a",
                        bodies={path: b"body"},
                    )

        for first, second in (("/Form/app.js", "/form/app.js"), ("/café.js", "/café.js")):
            with self.subTest(first=first, second=second):
                with self.assertRaises(ValueError):
                    ReleaseManifest(
                        "test-release-a",
                        "mhpss.event/1.0",
                        "test-cache-a",
                        (
                            {"path": first, "bytes": 1, "sha256": hashlib.sha256(b"a").hexdigest()},
                            {"path": second, "bytes": 1, "sha256": hashlib.sha256(b"b").hexdigest()},
                        ),
                    )


if __name__ == "__main__":
    unittest.main()
