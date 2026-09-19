#!/usr/bin/env python3
"""Atomic release and cache-integrity reference contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

SUPPORTED_CONTRACT_VERSION = "mhpss.event/1.0"
REQUIRED_RUNTIME_COMPONENTS = frozenset({"form", "hub", "contracts"})


class CacheIntegrityError(ValueError):
    """Cached assets do not match one complete release manifest."""


class MixedReleaseError(ValueError):
    """Runtime components do not belong to the same compatible release."""


@dataclass(frozen=True)
class ReleaseManifest:
    """Deterministic manifest for one paired form/hub/public release."""

    release_id: str
    contract_version: str
    cache_version: str
    assets: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        _identifier(self.release_id, "release_id")
        _identifier(self.contract_version, "contract_version")
        _identifier(self.cache_version, "cache_version")
        if not self.assets:
            raise ValueError("release manifest must contain at least one asset")
        frozen: list[Mapping[str, Any]] = []
        paths: set[str] = set()
        for entry in self.assets:
            if not isinstance(entry, Mapping) or set(entry) != {"path", "bytes", "sha256"}:
                raise ValueError("release asset entry fields are incomplete or unknown")
            path = entry["path"]
            byte_count = entry["bytes"]
            digest = entry["sha256"]
            if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
                raise ValueError("release asset paths must be absolute URL paths")
            if path in paths:
                raise ValueError(f"duplicate release asset path: {path}")
            paths.add(path)
            if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
                raise ValueError("release asset bytes must be a non-negative integer")
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise ValueError("release asset sha256 must be a lowercase SHA-256 digest")
            frozen.append(MappingProxyType({"path": path, "bytes": byte_count, "sha256": digest}))
        object.__setattr__(self, "assets", tuple(frozen))

    @classmethod
    def from_bodies(
        cls,
        *,
        release_id: str,
        contract_version: str,
        cache_version: str,
        bodies: dict[str, bytes],
    ) -> "ReleaseManifest":
        _identifier(release_id, "release_id")
        _identifier(contract_version, "contract_version")
        _identifier(cache_version, "cache_version")
        if not bodies:
            raise ValueError("release manifest must contain at least one asset")
        assets: list[dict[str, Any]] = []
        for path in sorted(bodies):
            body = bodies[path]
            if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
                raise ValueError("release asset paths must be absolute URL paths")
            if not isinstance(body, bytes):
                raise ValueError("release asset bodies must be bytes")
            assets.append(
                {
                    "path": path,
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                }
            )
        return cls(release_id, contract_version, cache_version, tuple(assets))

    def canonical_bytes(self) -> bytes:
        document = {
            "manifest_version": "mhpss.release/1.0",
            "release_id": self.release_id,
            "contract_version": self.contract_version,
            "cache_version": self.cache_version,
            "assets": [dict(entry) for entry in self.assets],
        }
        return json.dumps(document, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def verify_cached_release(
    manifest: ReleaseManifest, cached_bodies: dict[str, bytes]
) -> dict[str, Any]:
    """Verify exact path, byte-length, and digest parity for one release."""
    expected = {entry["path"]: entry for entry in manifest.assets}
    if set(cached_bodies) != set(expected):
        missing = sorted(set(expected) - set(cached_bodies))
        extra = sorted(set(cached_bodies) - set(expected))
        raise CacheIntegrityError(f"cache path mismatch; missing={missing}, extra={extra}")
    for path, entry in expected.items():
        body = cached_bodies[path]
        if not isinstance(body, bytes):
            raise CacheIntegrityError(f"cached body is not bytes: {path}")
        actual_digest = hashlib.sha256(body).hexdigest()
        if len(body) != entry["bytes"] or actual_digest != entry["sha256"]:
            raise CacheIntegrityError(
                f"cache body mismatch for {path}: expected {entry['sha256']}/{entry['bytes']}, "
                f"got {actual_digest}/{len(body)}"
            )
    return {
        "release_id": manifest.release_id,
        "contract_version": manifest.contract_version,
        "cache_version": manifest.cache_version,
        "manifest_sha256": manifest.digest(),
        "asset_count": len(expected),
    }


@dataclass(frozen=True)
class RuntimeProof:
    """Evidence that required components form one compatible runtime."""

    release_id: str
    contract_version: str


def verify_runtime_components(components: dict[str, dict[str, str]]) -> RuntimeProof:
    """Fail before event creation when assets come from mixed releases."""
    if set(components) != REQUIRED_RUNTIME_COMPONENTS:
        raise MixedReleaseError(
            f"runtime requires exactly {sorted(REQUIRED_RUNTIME_COMPONENTS)}"
        )
    release_ids: set[str] = set()
    contract_versions: set[str] = set()
    for name, component in components.items():
        if set(component) != {"release_id", "contract_version"}:
            raise MixedReleaseError(f"component metadata is incomplete or unknown: {name}")
        try:
            _identifier(component["release_id"], f"{name}.release_id")
            _identifier(component["contract_version"], f"{name}.contract_version")
        except ValueError as error:
            raise MixedReleaseError(str(error)) from error
        release_ids.add(component["release_id"])
        contract_versions.add(component["contract_version"])
    if len(release_ids) != 1 or len(contract_versions) != 1:
        raise MixedReleaseError(
            f"mixed runtime: release_ids={sorted(release_ids)}, "
            f"contract_versions={sorted(contract_versions)}"
        )
    contract_version = next(iter(contract_versions))
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise MixedReleaseError(f"unsupported runtime contract_version: {contract_version}")
    return RuntimeProof(next(iter(release_ids)), contract_version)


def _identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError(f"{label} must be a non-empty string of at most 128 characters")
