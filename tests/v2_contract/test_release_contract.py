#!/usr/bin/env python3
"""Atomic release, cache digest, and mixed-version contract tests."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "contracts"))

from release_contract import (  # noqa: E402
    CacheIntegrityError,
    MixedReleaseError,
    ReleaseManifest,
    verify_cached_release,
    verify_runtime_components,
)


class ReleaseContractTests(unittest.TestCase):
    def test_every_cached_body_must_match_one_complete_release(self) -> None:
        bodies = {
            "/index.html": b"<h1>synthetic</h1>",
            "/form/app.js": b"const release = 'a';\n",
            "/hub/app.css": b"body { color: black; }\n",
        }
        manifest = ReleaseManifest.from_bodies(
            release_id="test-release-a",
            contract_version="mhpss.event/1.0",
            cache_version="test-cache-a",
            bodies=bodies,
        )
        verified = verify_cached_release(manifest, bodies)
        self.assertEqual(verified["release_id"], "test-release-a")
        self.assertEqual(verified["asset_count"], 3)

    def test_tampered_truncated_swapped_missing_and_extra_cache_entries_fail_closed(self) -> None:
        bodies = {
            "/index.html": b"index-body",
            "/form/app.js": b"form-body",
            "/hub/app.js": b"hub-body",
        }
        manifest = ReleaseManifest.from_bodies(
            release_id="test-release-a",
            contract_version="mhpss.event/1.0",
            cache_version="test-cache-a",
            bodies=bodies,
        )
        variants = {
            "tampered": {**bodies, "/index.html": b"Index-body"},
            "truncated": {**bodies, "/form/app.js": b"form"},
            "swapped": {
                **bodies,
                "/form/app.js": bodies["/hub/app.js"],
                "/hub/app.js": bodies["/form/app.js"],
            },
            "missing": {key: value for key, value in bodies.items() if key != "/hub/app.js"},
            "extra": {**bodies, "/unexpected.js": b"no"},
        }
        for label, cached in variants.items():
            with self.subTest(label=label):
                with self.assertRaises(CacheIntegrityError):
                    verify_cached_release(manifest, cached)

    def test_runtime_components_must_share_release_and_contract_versions(self) -> None:
        bodies = {
            "/index.html": b"index-body",
            "/form/app.js": b"form-body",
            "/hub/app.js": b"hub-body",
        }
        manifest = ReleaseManifest.from_bodies(
            release_id="test-release-a",
            contract_version="mhpss.event/2.0",
            cache_version="test-cache-a",
            bodies=bodies,
        )
        components = {
            name: {
                "release_id": "test-release-a",
                "contract_version": "mhpss.event/2.0",
                "manifest_sha256": manifest.digest(),
            }
            for name in ("form", "hub", "contracts")
        }
        proof = verify_runtime_components(
            manifest=manifest,
            cached_bodies=bodies,
            components=components,
            trusted_manifest_sha256=manifest.digest(),
        )
        self.assertEqual(proof.release_id, "test-release-a")
        self.assertEqual(proof.contract_version, "mhpss.event/2.0")
        for field, bad_value in (
            ("release_id", "test-release-b"),
            ("contract_version", "mhpss.event/3.0"),
        ):
            with self.subTest(field=field):
                changed = {name: dict(value) for name, value in components.items()}
                changed["hub"][field] = bad_value
                with self.assertRaises(MixedReleaseError):
                    verify_runtime_components(
                        manifest=manifest,
                        cached_bodies=bodies,
                        components=changed,
                        trusted_manifest_sha256=manifest.digest(),
                    )

        for incomplete in ({}, {"form": components["form"]}):
            with self.subTest(incomplete=incomplete):
                with self.assertRaises(MixedReleaseError):
                    verify_runtime_components(
                        manifest=manifest,
                        cached_bodies=bodies,
                        components=incomplete,
                        trusted_manifest_sha256=manifest.digest(),
                    )
        unsupported = {name: {**value, "contract_version": "mhpss.event/3.0"} for name, value in components.items()}
        with self.assertRaises(MixedReleaseError):
            verify_runtime_components(
                manifest=manifest,
                cached_bodies=bodies,
                components=unsupported,
                trusted_manifest_sha256=manifest.digest(),
            )

    def test_manifest_digest_is_deterministic_and_covers_all_assets(self) -> None:
        bodies = {"/b": b"two", "/a": b"one"}
        first = ReleaseManifest.from_bodies(
            release_id="test-release-a",
            contract_version="mhpss.event/1.0",
            cache_version="test-cache-a",
            bodies=bodies,
        )
        second = ReleaseManifest.from_bodies(
            release_id="test-release-a",
            contract_version="mhpss.event/1.0",
            cache_version="test-cache-a",
            bodies=dict(reversed(list(bodies.items()))),
        )
        self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
        self.assertEqual(first.digest(), hashlib.sha256(first.canonical_bytes()).hexdigest())
        self.assertEqual([entry["path"] for entry in first.assets], ["/a", "/b"])

    def test_manifest_is_deeply_immutable_and_direct_construction_is_validated(self) -> None:
        manifest = ReleaseManifest.from_bodies(
            release_id="test-release-a",
            contract_version="mhpss.event/1.0",
            cache_version="test-cache-a",
            bodies={"/index.html": b"trusted"},
        )
        with self.assertRaises(TypeError):
            manifest.assets[0]["sha256"] = hashlib.sha256(b"attacker").hexdigest()

        with self.assertRaises(ValueError):
            ReleaseManifest("", "", "", ())
        with self.assertRaises(ValueError):
            ReleaseManifest(
                "test-release-a",
                "mhpss.event/1.0",
                "test-cache-a",
                (
                    {"path": "/same", "bytes": 1, "sha256": "0" * 64},
                    {"path": "/same", "bytes": 1, "sha256": "1" * 64},
                ),
            )


if __name__ == "__main__":
    unittest.main()
