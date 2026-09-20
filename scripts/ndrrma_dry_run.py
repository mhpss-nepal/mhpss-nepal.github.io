#!/usr/bin/env python3
"""Exercise the NDRRMA capture pipeline entirely with synthetic data, offline.

This is the dry-run harness: it never touches the network and never reads the
real asset, so the ledger's per-day idempotence and the timezone guard can be
proven locally. It prints a single JSON report and exits 0.
"""

from __future__ import annotations

import datetime as dt
import json
import tempfile
from pathlib import Path

from ndrrma_capture import WIB, capture_payloads

SECTORS = {
    "WASH": 52412,
    "Food Security": 28099,
    "Shelter": 23232,
    "Education": 12236,
    "Protection - GBV": 6425,
    "Protection - MHPSS": 5830,
    "Health": 4074,
    "Protection - Child Protection": 3484,
    "Health - SRH": 789,
    "CCCM": 344,
    "Nutrition": 28,
}
FIRST_TIME = dt.datetime(2026, 9, 21, 9, 0, tzinfo=WIB)


def sector_payload(values: dict[str, int]) -> dict[str, object]:
    labels = list(values)
    rows = []
    for index, label in enumerate(labels):
        row: dict[str, object] = {"C": [index, values[label]]}
        if index == 0:
            row["S"] = [{"DN": "D0"}, {}]
        rows.append(row)
    return {
        "results": [{"result": {"data": {"timestamp": "2026-09-20T02:00:00Z", "dsr": {"DS": [{
            "ValueDicts": {"D0": labels},
            "PH": [{"DM0": [{"M": [{"DM1": rows}]}]}],
        }]}}}}],
    }


def date_payload(value: dt.date) -> dict[str, object]:
    milliseconds = int(dt.datetime.combine(value, dt.time(), tzinfo=dt.timezone.utc).timestamp() * 1000)
    return {
        "results": [{"result": {"data": {"dsr": {"DS": [{
            "PH": [{"DM0": [{"M0": milliseconds}]}],
        }]}}}}],
    }


def moved(values: dict[str, int], reached: int) -> dict[str, int]:
    updated = dict(values)
    updated["Protection - MHPSS"] = reached
    return updated


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary_directory:
        asset = Path(temporary_directory)
        first = capture_payloads(asset, sector_payload(SECTORS), date_payload(dt.date(2026, 9, 19)), now=FIRST_TIME)
        retry = capture_payloads(
            asset,
            sector_payload(SECTORS),
            date_payload(dt.date(2026, 9, 19)),
            now=FIRST_TIME + dt.timedelta(hours=1),
        )
        ledger_after_retry = (asset / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
        next_week = capture_payloads(
            asset,
            sector_payload(moved(SECTORS, 6001)),
            date_payload(dt.date(2026, 9, 26)),
            now=FIRST_TIME + dt.timedelta(days=7),
        )
        versions = sorted(path.name for path in (asset / "versions").glob("*.json"))
        latest = json.loads((asset / "public" / "latest.json").read_text(encoding="utf-8"))

    # Separate run: a UTC-labelled instant must still be written with the WIB offset.
    with tempfile.TemporaryDirectory() as temporary_directory:
        utc_asset = Path(temporary_directory)
        utc_result = capture_payloads(
            utc_asset,
            sector_payload(SECTORS),
            date_payload(dt.date(2026, 9, 19)),
            now=dt.datetime(2026, 9, 20, 17, 30, tzinfo=dt.timezone.utc),
        )
        utc_latest = json.loads((utc_asset / "public" / "latest.json").read_text(encoding="utf-8"))

    report = {
        "synthetic_only": True,
        "network_used": False,
        "first_capture": {"changed": first.changed, "paths": list(first.written_paths)},
        "same_day_retry": {
            "changed": retry.changed,
            "wrote_anything": bool(retry.written_paths),
            "ledger_rows": len(ledger_after_retry),
        },
        "moved_source": {
            "changed": next_week.changed,
            "versions": versions,
            "mhpss_reached": latest["aggregates"]["mhpss_reached"],
        },
        "timezone": {
            "capture_day": utc_result.capture_day,
            "capture_date": utc_latest["capture_date"],
            "capture_offset": utc_latest["capture_date"][-6:],
        },
    }
    print(json.dumps(report, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
