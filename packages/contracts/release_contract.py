#!/usr/bin/env python3
"""Trusted, manifest-bound release and cache-integrity contracts."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

SUPPORTED_CONTRACT_VERSION = "mhpss.event/2.0"
REQUIRED_RUNTIME_COMPONENTS = frozenset({"form", "hub", "contracts"})
_WINDOWS_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)
class CacheIntegrityError(ValueError):
    """Cached assets do not match one complete release manifest."""


class MixedReleaseError(ValueError):
    """Runtime components do not prove one trusted release manifest."""


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
        collision_keys: dict[str, str] = {}
        for entry in self.assets:
            if not isinstance(entry, Mapping) or set(entry) != {"path", "bytes", "sha256"}:
                raise ValueError("release asset entry fields are incomplete or unknown")
            path = _canonical_asset_path(entry["path"])
            collision_key = unicodedata.normalize("NFC", path).casefold()
            if collision_key in collision_keys:
                raise ValueError(
                    f"release asset path collision: {collision_keys[collision_key]} and {path}"
                )
            collision_keys[collision_key] = path
            byte_count = entry["bytes"]
            digest = entry["sha256"]
            if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
                raise ValueError("release asset bytes must be a non-negative integer")
            if not _is_digest(digest):
                raise ValueError("release asset sha256 must be a lowercase SHA-256 digest")
            frozen.append(MappingProxyType({"path": path, "bytes": byte_count, "sha256": digest}))
        frozen.sort(key=lambda item: item["path"])
        object.__setattr__(self, "assets", tuple(frozen))

    @classmethod
    def from_bodies(
        cls,
        *,
        release_id: str,
        contract_version: str,
        cache_version: str,
        bodies: Mapping[str, bytes],
    ) -> "ReleaseManifest":
        if not isinstance(bodies, Mapping) or not bodies:
            raise ValueError("release manifest must contain at least one asset")
        assets: list[dict[str, Any]] = []
        for supplied_path, body in bodies.items():
            path = _canonical_asset_path(supplied_path)
            if not isinstance(body, bytes):
                raise ValueError("release asset bodies must be bytes")
            assets.append(
                {"path": path, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
            )
        return cls(release_id, contract_version, cache_version, tuple(assets))

    def canonical_bytes(self) -> bytes:
        document = {
            "manifest_version": "mhpss.release/2.0",
            "release_id": self.release_id,
            "contract_version": self.contract_version,
            "cache_version": self.cache_version,
            "assets": [dict(entry) for entry in self.assets],
        }
        return json.dumps(document, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def verify_cached_release(
    manifest: ReleaseManifest, cached_bodies: Mapping[str, bytes]
) -> dict[str, Any]:
    """Verify exact canonical path, byte-length, and digest parity."""
    expected = {entry["path"]: entry for entry in manifest.assets}
    try:
        supplied = {_canonical_asset_path(path): body for path, body in cached_bodies.items()}
    except (AttributeError, TypeError, ValueError) as error:
        raise CacheIntegrityError(str(error)) from error
    if len(supplied) != len(cached_bodies) or set(supplied) != set(expected):
        missing = sorted(set(expected) - set(supplied))
        extra = sorted(set(supplied) - set(expected))
        raise CacheIntegrityError(f"cache path mismatch; missing={missing}, extra={extra}")
    for path, entry in expected.items():
        body = supplied[path]
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


def _make_runtime_api():
    seal = object()

    class VerifiedRuntime:
        """Closure-private evidence emitted only by full manifest verification."""

        __slots__ = ("release_id", "contract_version", "manifest_sha256", "_seal")

        def __init__(
            self,
            release_id: str,
            contract_version: str,
            manifest_sha256: str,
            *,
            supplied_seal: object,
        ) -> None:
            if supplied_seal is not seal:
                raise TypeError("runtime proof can only be issued by trusted verification")
            self.release_id = release_id
            self.contract_version = contract_version
            self.manifest_sha256 = manifest_sha256
            self._seal = seal

    def verify(
        *,
        manifest: ReleaseManifest,
        cached_bodies: Mapping[str, bytes],
        components: Mapping[str, Mapping[str, str]],
        trusted_manifest_sha256: str,
    ) -> object:
        if not isinstance(manifest, ReleaseManifest) or not _is_digest(trusted_manifest_sha256):
            raise MixedReleaseError("trusted release manifest evidence is invalid")
        verified = verify_cached_release(manifest, cached_bodies)
        if verified["manifest_sha256"] != trusted_manifest_sha256:
            raise MixedReleaseError("release manifest is not the trusted manifest")
        if set(components) != REQUIRED_RUNTIME_COMPONENTS:
            raise MixedReleaseError(
                f"runtime requires exactly {sorted(REQUIRED_RUNTIME_COMPONENTS)}"
            )
        required_metadata = {"release_id", "contract_version", "manifest_sha256"}
        for name, component in components.items():
            if not isinstance(component, Mapping) or set(component) != required_metadata:
                raise MixedReleaseError(f"component metadata is incomplete or unknown: {name}")
            if (
                component["release_id"] != manifest.release_id
                or component["contract_version"] != manifest.contract_version
                or component["manifest_sha256"] != trusted_manifest_sha256
            ):
                raise MixedReleaseError(f"component is not bound to the trusted manifest: {name}")
        if manifest.contract_version != SUPPORTED_CONTRACT_VERSION:
            raise MixedReleaseError(
                f"unsupported runtime contract_version: {manifest.contract_version}"
            )
        return VerifiedRuntime(
            manifest.release_id,
            manifest.contract_version,
            trusted_manifest_sha256,
            supplied_seal=seal,
        )

    def values(proof: object) -> tuple[str, str, str]:
        if not isinstance(proof, VerifiedRuntime) or proof._seal is not seal:
            raise MixedReleaseError("runtime proof was not issued by trusted verification")
        return proof.release_id, proof.contract_version, proof.manifest_sha256

    return verify, values


verify_runtime_components, runtime_proof_values = _make_runtime_api()
del _make_runtime_api


def _canonical_asset_path(value: object) -> str:
    if not isinstance(value, str) or not value.startswith("/") or len(value) > 2048:
        raise ValueError("release asset path must be a bounded absolute URL path")
    if value == "/" or "%" in value or "\\" in value or unicodedata.normalize("NFC", value) != value:
        raise ValueError("release asset path must use one canonical unencoded form")
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise ValueError("release asset path contains a control or format character")
    components = value[1:].split("/")
    if not components or any(not component or component in {".", ".."} for component in components):
        raise ValueError("release asset path contains an empty, dot, or traversal component")
    for component in components:
        if len(component) > 255 or component.endswith((".", " ")):
            raise ValueError("release asset path contains an unsafe component")
        base = component.split(".", 1)[0].upper()
        if base in _WINDOWS_RESERVED:
            raise ValueError("release asset path contains a reserved component")
    return value


def _identifier(value: object, label: str) -> None:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError(f"{label} must be a non-empty string of at most 128 characters")
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise ValueError(f"{label} contains a control or format character")


def _is_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )