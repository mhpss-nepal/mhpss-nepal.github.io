#!/usr/bin/env python3
"""Capture public NDRRMA 5Ws aggregates with no AI, account, or secret.

Read-only against the source: it posts the report's own public-embed semantic
query over plain HTTPS and parses the response. Beneath an explicitly supplied
asset directory it writes:

    versions/<capture-stamp>.json  one immutable record per source movement
    public/latest.json           public-safe aggregate for Layer 3 to consume
    ledger.jsonl                 append-only provenance ledger

A run is a "movement" when the observed ``(data_date, source_payload_sha256)``
pair differs from the newest ledger row. When the source has not moved the run
writes nothing at all, so an unchanged source never produces a repository diff
and therefore never produces a commit. That is what keeps the weekly job quiet.

Only figures already published on the public NDRRMA dashboard are written; the
committed artifact carries provenance (``capture_date``, ``data_date``,
``last_successful_refresh``, ``success``) so the site can show both dates and
report "checked on X, source still carries data as of Y".
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime as dt
import gzip
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

WIB = dt.timezone(dt.timedelta(hours=7), name="WIB")
DEFAULT_ASSET_DIR = Path("data/ndrrma")
DEFAULT_QUERY_CONFIG = Path("config/ndrrma-powerbi-query.json")
SOURCE_NAME = "NDRRMA 5Ws public Power BI dashboard"
SOURCE_REPORT = "Rasuwa Flood Response"
SOURCE_ACCESS = "public embed semantic query; read-only; no account or token"
# Response-wide headline published separately by the report, not the sum of the
# sector rows (sector reach is non-additive: max per location).
RESPONSE_HEADLINE = 61612
MHPSS_ACTIVITIES = 233
# The full public sector set, used only to reject a partial response. The
# per-sector breakdown is deliberately not written into the repository.
EXPECTED_SECTORS = (
    "WASH",
    "Food Security",
    "Shelter",
    "Education",
    "Protection - GBV",
    "Protection - MHPSS",
    "Health",
    "Protection - Child Protection",
    "Health - SRH",
    "CCCM",
    "Nutrition",
)


@dataclasses.dataclass(frozen=True)
class CaptureResult:
    capture_day: str
    changed: bool
    written_paths: tuple[str, ...]
    sha256_by_path: dict[str, str]


def _strict_json_loads(text: str) -> Any:
    """Parse JSON with duplicate keys and non-finite values rejected."""

    def reject_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite JSON value: {token}")

    return json.loads(text, object_pairs_hook=reject_pairs, parse_constant=reject_constant)


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")


def _sector_rows(dataset: dict[str, Any]) -> Iterable[tuple[list[dict[str, Any]], list[Any]]]:
    """Yield (schema, cells) for the 'sector x measure' shape.

    Power BI emits the column schema once and omits it on later rows
    (run-length encoding), so the last seen schema is carried forward.
    """
    headers = dataset.get("PH")
    if not isinstance(headers, list) or not headers:
        return
    last_schema = None
    for outer in headers[0].get("DM0", []):
        for group in outer.get("M", []):
            for row in group.get("DM1", []):
                if "S" in row:
                    last_schema = row["S"]
                if last_schema is not None and "C" in row:
                    yield last_schema, row["C"]


def parse_sector_response(payload: dict[str, Any]) -> dict[str, int | float]:
    """Return {sector label: reach} from a sector x measure response."""
    try:
        dataset = payload["results"][0]["result"]["data"]["dsr"]["DS"][0]
        dictionaries = dataset.get("ValueDicts", {})
        result: dict[str, int | float] = {}
        for schema, cells in _sector_rows(dataset):
            dictionary_index = next((index for index, column in enumerate(schema) if column.get("DN")), None)
            value_index = next((index for index, column in enumerate(schema) if not column.get("DN")), None)
            if dictionary_index is None or value_index is None or len(cells) <= max(dictionary_index, value_index):
                continue
            labels = dictionaries.get(schema[dictionary_index]["DN"], [])
            label_index = cells[dictionary_index]
            value = cells[value_index]
            if (
                isinstance(label_index, int)
                and not isinstance(value, bool)
                and isinstance(value, (int, float))
                and 0 <= label_index < len(labels)
            ):
                result[labels[label_index]] = value
    except (IndexError, KeyError, TypeError) as error:
        raise ValueError("malformed sector response") from error
    if not result:
        raise ValueError("no sector rows found")
    missing = [sector for sector in EXPECTED_SECTORS if sector not in result]
    if missing:
        raise ValueError(f"sector response is incomplete: {', '.join(missing)}")
    return result


def parse_data_date(payload: dict[str, Any]) -> str:
    """Return the report's ``Max(Data Refresh.Date)`` as ``YYYY-MM-DD`` (UTC)."""
    try:
        dataset = payload["results"][0]["result"]["data"]["dsr"]["DS"][0]
        entry = dataset["PH"][0]["DM0"][0]
        # A single-value card stores the number under M0, or in C.
        milliseconds = entry.get("M0")
        if milliseconds is None:
            cells = entry.get("C") or []
            milliseconds = cells[0] if cells else None
        if not isinstance(milliseconds, (int, float)) or isinstance(milliseconds, bool):
            raise ValueError("data-date response has no timestamp")
        return dt.datetime.fromtimestamp(milliseconds / 1000, tz=dt.timezone.utc).date().isoformat()
    except (IndexError, KeyError, TypeError) as error:
        raise ValueError("malformed data-date response") from error


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def verify_readback(path: Path, expected_sha256: str) -> None:
    """Exact read-back: a successful write is not proof the file is correct."""
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ValueError(f"exact read-back verification failed for {path}: {actual} != {expected_sha256}")


def require_archive_root(member_names: Iterable[str], expected_root: str) -> None:
    """Guard an archive's root name: a mismatch makes a remote swap silently stale."""
    roots = {PurePosixPath(name).parts[0] for name in member_names if PurePosixPath(name).parts}
    if roots != {expected_root}:
        raise ValueError(f"archive root {sorted(roots)} != {expected_root}")


def _validate_asset_directory(asset_dir: Path, *, require_existing: bool) -> Path:
    asset_dir = asset_dir.expanduser()
    if require_existing and not asset_dir.is_dir():
        # Never guess or create the asset path: an explicit path is the whole point.
        # This is what broke when the script lived outside the asset and used __file__.
        raise FileNotFoundError(f"asset directory not found: {asset_dir}")
    if asset_dir.exists() and not asset_dir.is_dir():
        raise ValueError(f"asset path is not a directory: {asset_dir}")
    return asset_dir


def _normalize_now(now: dt.datetime | None) -> dt.datetime:
    # Pin WIB here; never inherit TZ. A UTC runner must still label the capture WIB.
    if now is None:
        return dt.datetime.now(WIB)
    if now.tzinfo is None:
        raise ValueError("capture time must be timezone-aware")
    return now.astimezone(WIB)


def _load_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = _strict_json_loads(line)
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"malformed ledger line {line_number}") from error
        if not isinstance(row, dict) or not isinstance(row.get("capture_day"), str):
            raise ValueError(f"invalid ledger line {line_number}")
        rows.append(row)
    return rows


def _write_verified(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    if temporary.exists():
        temporary.unlink()
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    digest = sha256_bytes(data)
    verify_readback(path, digest)
    return digest


def _source_moved(ledger_rows: list[dict[str, Any]], data_date: str, payload_sha256: str) -> bool:
    if not ledger_rows:
        return True
    newest = max(ledger_rows, key=lambda row: (row["capture_day"], row.get("capture_date", "")))
    return not (
        newest.get("data_date") == data_date
        and newest.get("source_payload_sha256") == payload_sha256
        and newest.get("success") is True
    )


def capture_payloads(
    asset_dir: Path,
    sector_payload: dict[str, Any],
    date_payload: dict[str, Any],
    *,
    now: dt.datetime | None = None,
) -> CaptureResult:
    """Write the public aggregate when the source moved; otherwise write nothing."""
    asset_dir = _validate_asset_directory(Path(asset_dir), require_existing=False)
    captured_at = _normalize_now(now).isoformat(timespec="minutes")
    capture_day = captured_at[:10]
    # Version id keeps every movement immutable and unique even if the source
    # moves twice on the same WIB day; a bare date filename would overwrite.
    version_id = captured_at.replace(":", "")
    sectors = parse_sector_response(sector_payload)
    data_date = parse_data_date(date_payload)
    source_payload_sha256 = sha256_bytes(_canonical_json(sector_payload))

    ledger_path = asset_dir / "ledger.jsonl"
    ledger_rows = _load_ledger(ledger_path)
    if not _source_moved(ledger_rows, data_date, source_payload_sha256):
        # Watchdog: the source has not moved, so leave every committed byte alone.
        return CaptureResult(capture_day=capture_day, changed=False, written_paths=(), sha256_by_path={})

    record = {
        "schema_version": 1,
        "capture_date": captured_at,
        "data_date": data_date,
        "last_successful_refresh": captured_at,
        "success": True,
        "source": {"name": SOURCE_NAME, "report": SOURCE_REPORT, "access": SOURCE_ACCESS},
        "aggregates": {
            "mhpss_reached": sectors["Protection - MHPSS"],
            "response_headline": RESPONSE_HEADLINE,
            "mhpss_activities": MHPSS_ACTIVITIES,
        },
        "publication": {
            "classification": "public",
            "scope": "figures already published on the public NDRRMA dashboard",
            "note": "Sector reach is non-additive; never sum sector rows.",
        },
    }
    record_bytes = _canonical_json(record)
    version_relative = f"versions/{version_id}.json"
    public_relative = "public/latest.json"
    ledger_entry = {
        "schema_version": 1,
        "capture_date": captured_at,
        "capture_day": capture_day,
        "data_date": data_date,
        "last_successful_refresh": captured_at,
        "success": True,
        "source": SOURCE_NAME,
        "source_payload_sha256": source_payload_sha256,
        "version_path": version_relative,
        "version_sha256": sha256_bytes(record_bytes),
        "public_artifact_path": public_relative,
        "public_artifact_sha256": sha256_bytes(record_bytes),
    }
    # Append-only: an existing row is never edited. A repeated capture day for the
    # same movement is already excluded by the movement check above.
    ledger_rows.append(ledger_entry)
    ledger_rows.sort(key=lambda row: (row["capture_day"], row.get("capture_date", "")))
    ledger_bytes = b"".join(_canonical_json(row) for row in ledger_rows)

    written = {
        version_relative: _write_verified(asset_dir / version_relative, record_bytes),
        public_relative: _write_verified(asset_dir / public_relative, record_bytes),
        "ledger.jsonl": _write_verified(ledger_path, ledger_bytes),
    }
    return CaptureResult(
        capture_day=capture_day,
        changed=True,
        written_paths=tuple(sorted(written)),
        sha256_by_path=dict(written),
    )


def repository_paths(result: CaptureResult, asset_dir: Path) -> tuple[str, ...]:
    prefix = PurePosixPath(asset_dir.as_posix())
    return tuple(sorted((prefix / PurePosixPath(path)).as_posix() for path in result.written_paths))


def _post(api: str, resource_key: str, body: dict[str, Any], tag: str) -> dict[str, Any]:
    query = copy.deepcopy(body)
    semantic_query = query["queries"][0]
    semantic_query["CacheKey"] = json.dumps(semantic_query["Query"], separators=(",", ":"))
    data = json.dumps(query, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        api,
        data=data,
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip",
            "X-PowerBI-ResourceKey": resource_key,
            "ActivityId": "github-actions-ndrrma-capture",
            "RequestId": f"{tag}-{int(dt.datetime.now(WIB).timestamp() * 1000)}",
            "User-Agent": "mhpss-nepal-ndrrma-capture/1",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"Power BI returned HTTP {response.status}")
        raw = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    parsed = _strict_json_loads(raw.decode("utf-8", "strict"))
    if not isinstance(parsed, dict):
        raise ValueError("Power BI response is not a JSON object")
    return parsed


def fetch_payloads(query_config: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = _strict_json_loads(query_config.read_text(encoding="utf-8"))
    required = ("api", "resource_key", "sector_query", "date_query")
    if not isinstance(config, dict) or config.get("schema") != 1 or any(key not in config for key in required):
        raise ValueError("query configuration is invalid")
    return (
        _post(config["api"], config["resource_key"], config["sector_query"], "sector"),
        _post(config["api"], config["resource_key"], config["date_query"], "date"),
    )


def verify_artifacts(asset_dir: Path) -> dict[str, Any]:
    """Strictly re-validate committed artifacts; never touches the network.

    Fails loudly on malformed JSON, a ledger row whose recorded hash does not
    match the file it names, or a public artifact that is not the newest version.
    """
    asset_dir = _validate_asset_directory(asset_dir, require_existing=True)
    ledger_path = asset_dir / "ledger.jsonl"
    if not ledger_path.exists():
        raise ValueError("ledger.jsonl is missing")
    rows = _load_ledger(ledger_path)
    if not rows:
        raise ValueError("ledger.jsonl is empty")
    for row in rows:
        for key in ("version_path", "version_sha256", "public_artifact_path", "public_artifact_sha256"):
            if not isinstance(row.get(key), str):
                raise ValueError(f"ledger row {row.get('capture_day')!r} is missing {key}")
        verify_readback(asset_dir / row["version_path"], row["version_sha256"])
    newest = max(rows, key=lambda row: (row["capture_day"], row.get("capture_date", "")))
    public_path = asset_dir / newest["public_artifact_path"]
    verify_readback(public_path, newest["public_artifact_sha256"])
    artifact = _strict_json_loads(public_path.read_text(encoding="utf-8"))
    if not isinstance(artifact, dict):
        raise ValueError("public artifact is not a JSON object")
    required = ("schema_version", "capture_date", "data_date", "last_successful_refresh", "success", "source", "aggregates", "publication")
    for key in required:
        if key not in artifact:
            raise ValueError(f"public artifact is missing {key!r}")
    if "sector_totals" in artifact.get("aggregates", {}):
        raise ValueError("public artifact must not contain a per-sector breakdown")
    if artifact.get("publication", {}).get("classification") != "public":
        raise ValueError("public artifact is not classified public")
    return {
        "rows": len(rows),
        "newest_capture_day": newest["capture_day"],
        "newest_data_date": newest["data_date"],
        "verified": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR)
    parser.add_argument("--query-config", type=Path, default=DEFAULT_QUERY_CONFIG)
    parser.add_argument("--sector-fixture", type=Path, help="offline synthetic sector response")
    parser.add_argument("--date-fixture", type=Path, help="offline synthetic data-date response")
    parser.add_argument("--capture-time", help="ISO8601 test override; must include an offset")
    parser.add_argument("--verify", action="store_true", help="re-validate committed artifacts only")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    try:
        asset_dir = _validate_asset_directory(arguments.asset_dir, require_existing=True)
        if arguments.verify:
            print(json.dumps(verify_artifacts(asset_dir), separators=(",", ":"), sort_keys=True))
            return 0
        if bool(arguments.sector_fixture) != bool(arguments.date_fixture):
            raise ValueError("sector and date fixtures must be supplied together")
        if arguments.sector_fixture:
            assert arguments.date_fixture is not None
            sector_payload = _strict_json_loads(arguments.sector_fixture.read_text(encoding="utf-8"))
            date_payload = _strict_json_loads(arguments.date_fixture.read_text(encoding="utf-8"))
        else:
            sector_payload, date_payload = fetch_payloads(arguments.query_config)
        now = dt.datetime.fromisoformat(arguments.capture_time) if arguments.capture_time else None
        result = capture_payloads(asset_dir, sector_payload, date_payload, now=now)
        print(json.dumps({
            "capture_day": result.capture_day,
            "changed": result.changed,
            "paths": repository_paths(result, arguments.asset_dir),
        }, separators=(",", ":"), sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError, urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"NDRRMA capture failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
