#!/usr/bin/env python3
"""Synthetic, offline tests for the AI-free NDRRMA capture pipeline.

Failing-first coverage for the standalone capture script, the guarded commit
step, and the workflow contract. No network access and no real source payloads:
every fixture here is synthetic, matching the public source's response *shape*
only.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CAPTURE_SCRIPT = REPOSITORY_ROOT / "scripts" / "ndrrma_capture.py"
DRY_RUN_SCRIPT = REPOSITORY_ROOT / "scripts" / "ndrrma_dry_run.py"
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ndrrma-weekly.yml"
WIB = dt.timezone(dt.timedelta(hours=7))
ALLOWED_STDLIB_IMPORTS = {
    "__future__",
    "argparse",
    "copy",
    "dataclasses",
    "datetime",
    "gzip",
    "hashlib",
    "json",
    "os",
    "pathlib",
    "sys",
    "typing",
    "urllib",
}
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


def load_capture_module():
    spec = importlib.util.spec_from_file_location("ndrrma_capture", CAPTURE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load capture module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def synthetic_sector_payload(values: dict[str, int] | None = None) -> dict[str, object]:
    values = values or SECTORS
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


def synthetic_date_payload(data_date: dt.date = dt.date(2026, 9, 19)) -> dict[str, object]:
    milliseconds = int(dt.datetime.combine(data_date, dt.time(), tzinfo=dt.timezone.utc).timestamp() * 1000)
    return {
        "results": [{"result": {"data": {"dsr": {"DS": [{
            "PH": [{"DM0": [{"M0": milliseconds}]}],
        }]}}}}],
    }


class NdrrmaCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        if not CAPTURE_SCRIPT.exists():
            self.fail(f"capture script is missing: {CAPTURE_SCRIPT}")
        self.capture = load_capture_module()

    def test_parse_sector_response_extracts_public_aggregate(self) -> None:
        aggregate = self.capture.parse_sector_response(synthetic_sector_payload())
        self.assertEqual(aggregate["Protection - MHPSS"], 5830)
        self.assertEqual(len(aggregate), 11)

    def test_parse_sector_response_rejects_malformed_response(self) -> None:
        with self.assertRaisesRegex(ValueError, "sector"):
            self.capture.parse_sector_response({"unexpected": True})
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.capture.parse_sector_response(synthetic_sector_payload({"WASH": 1}))

    def test_parse_data_date_extracts_source_refresh_date(self) -> None:
        self.assertEqual(self.capture.parse_data_date(synthetic_date_payload()), "2026-09-19")

    def test_missing_asset_directory_fails_without_creating_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing"
            completed = subprocess.run(
                [sys.executable, str(CAPTURE_SCRIPT), "--asset-dir", str(missing)],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("asset directory not found", completed.stderr)
            self.assertFalse(missing.exists())

    def test_utc_runner_still_records_wib_capture_date(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            asset = Path(temporary_directory)
            now_utc = dt.datetime(2026, 9, 20, 17, 30, tzinfo=dt.timezone.utc)
            result = self.capture.capture_payloads(
                asset,
                synthetic_sector_payload(),
                synthetic_date_payload(),
                now=now_utc,
            )
            provenance = json.loads((asset / "public" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(result.capture_day, "2026-09-21")
            self.assertEqual(provenance["capture_date"], "2026-09-21T00:30+07:00")
            self.assertEqual(provenance["last_successful_refresh"], "2026-09-21T00:30+07:00")
            self.assertEqual(provenance["success"], True)
            self.assertEqual(provenance["data_date"], "2026-09-19")

    def test_unchanged_source_writes_nothing_and_leaves_a_clean_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            asset = Path(temporary_directory)
            now = dt.datetime(2026, 9, 21, 9, 0, tzinfo=WIB)
            first = self.capture.capture_payloads(
                asset, synthetic_sector_payload(), synthetic_date_payload(), now=now
            )
            before = {path.relative_to(asset): path.read_bytes() for path in asset.rglob("*") if path.is_file()}
            second = self.capture.capture_payloads(
                asset, synthetic_sector_payload(), synthetic_date_payload(), now=now + dt.timedelta(hours=1)
            )
            after = {path.relative_to(asset): path.read_bytes() for path in asset.rglob("*") if path.is_file()}
            self.assertTrue(first.changed)
            self.assertFalse(second.changed)
            self.assertEqual(second.written_paths, ())
            self.assertEqual(before, after)
            self.assertEqual(len((asset / "ledger.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    def test_moved_source_creates_versioned_snapshot_and_public_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            asset = Path(temporary_directory)
            first_now = dt.datetime(2026, 9, 21, 9, 0, tzinfo=WIB)
            self.capture.capture_payloads(asset, synthetic_sector_payload(), synthetic_date_payload(), now=first_now)
            moved = dict(SECTORS)
            moved["Protection - MHPSS"] = 6001
            result = self.capture.capture_payloads(
                asset,
                synthetic_sector_payload(moved),
                synthetic_date_payload(dt.date(2026, 9, 26)),
                now=first_now + dt.timedelta(days=7),
            )
            artifact = json.loads((asset / "public" / "latest.json").read_text(encoding="utf-8"))
            version_names = sorted(path.name for path in (asset / "versions").glob("*.json"))
            self.assertTrue(result.changed)
            self.assertEqual(
                version_names,
                ["2026-09-21T0900+0700.json", "2026-09-28T0900+0700.json"],
            )
            self.assertEqual(artifact["schema_version"], 1)
            self.assertEqual(artifact["data_date"], "2026-09-26")
            self.assertEqual(artifact["source"]["name"], "NDRRMA 5Ws public Power BI dashboard")
            self.assertEqual(artifact["success"], True)
            self.assertEqual(artifact["aggregates"]["mhpss_reached"], 6001)
            self.assertEqual(artifact["aggregates"]["response_headline"], 61612)
            # The public artifact must not leak private per-sector or person-level data.
            self.assertNotIn("sector_totals", artifact)

    def test_ledger_and_snapshot_are_traceable_and_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            asset = Path(temporary_directory)
            result = self.capture.capture_payloads(
                asset,
                synthetic_sector_payload(),
                synthetic_date_payload(),
                now=dt.datetime(2026, 9, 21, 9, 0, tzinfo=WIB),
            )
            expected = {
                "data/ndrrma/ledger.jsonl",
                "data/ndrrma/public/latest.json",
                "data/ndrrma/versions/2026-09-21T0900+0700.json",
            }
            self.assertEqual(set(self.capture.repository_paths(result, Path("data/ndrrma"))), expected)
            for relative in result.written_paths:
                absolute = asset / relative
                self.assertEqual(self.capture.sha256_file(absolute), result.sha256_by_path[relative])
            ledger_row = json.loads((asset / "ledger.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(
                self.capture.sha256_file(asset / ledger_row["version_path"]),
                ledger_row["version_sha256"],
            )
            self.assertEqual(
                self.capture.sha256_file(asset / ledger_row["public_artifact_path"]),
                ledger_row["public_artifact_sha256"],
            )

    def test_corrupted_output_is_caught_by_exact_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "artifact.json"
            path.write_text("one\n", encoding="utf-8")
            digest = self.capture.sha256_file(path)
            self.capture.verify_readback(path, digest)
            path.write_text("two\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "read-back"):
                self.capture.verify_readback(path, digest)

    def test_verify_artifacts_accepts_a_real_capture_and_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            asset = Path(temporary_directory)
            self.capture.capture_payloads(
                asset,
                synthetic_sector_payload(),
                synthetic_date_payload(),
                now=dt.datetime(2026, 9, 21, 9, 0, tzinfo=WIB),
            )
            report = self.capture.verify_artifacts(asset)
            self.assertEqual(report["verified"], True)
            self.assertEqual(report["newest_data_date"], "2026-09-19")

            version_file = next((asset / "versions").glob("*.json"))
            version_file.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "read-back"):
                self.capture.verify_artifacts(asset)

    def test_verify_artifacts_rejects_a_public_artifact_with_a_sector_breakdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            asset = Path(temporary_directory)
            self.capture.capture_payloads(
                asset,
                synthetic_sector_payload(),
                synthetic_date_payload(),
                now=dt.datetime(2026, 9, 21, 9, 0, tzinfo=WIB),
            )
            public_path = asset / "public" / "latest.json"
            artifact = json.loads(public_path.read_text(encoding="utf-8"))
            artifact["aggregates"]["sector_totals"] = {"WASH": 1}
            public_bytes = (json.dumps(artifact, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
            public_path.write_bytes(public_bytes)
            # Keep the ledger digest in step so the *content* rule, not the hash rule, fails.
            ledger_path = asset / "ledger.jsonl"
            row = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
            row["public_artifact_sha256"] = self.capture.sha256_bytes(public_bytes)
            ledger_path.write_text(
                json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "per-sector"):
                self.capture.verify_artifacts(asset)

    def test_archive_root_guard_rejects_a_mismatched_root(self) -> None:
        self.capture.require_archive_root(["NDRRMA-Public-Data/file.json"], "NDRRMA-Public-Data")
        with self.assertRaisesRegex(ValueError, "archive root"):
            self.capture.require_archive_root(["wrong/file.json"], "NDRRMA-Public-Data")

    def test_malformed_fixture_run_fails_without_publishing_or_dirtying(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            asset = Path(temporary_directory)
            (asset / "sector.json").write_text("{not json", encoding="utf-8")
            (asset / "date.json").write_text(json.dumps(synthetic_date_payload()), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(CAPTURE_SCRIPT),
                    "--asset-dir",
                    str(asset),
                    "--sector-fixture",
                    str(asset / "sector.json"),
                    "--date-fixture",
                    str(asset / "date.json"),
                    "--capture-time",
                    "2026-09-21T09:00:00+07:00",
                ],
                cwd=REPOSITORY_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertFalse((asset / "public" / "latest.json").exists())
            self.assertFalse((asset / "ledger.jsonl").exists())

    def test_dry_run_harness_proves_offline_unchanged_and_moved_paths(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(DRY_RUN_SCRIPT)],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            env={**os.environ, "TZ": "UTC"},
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["same_day_retry"]["changed"], False)
        self.assertEqual(report["same_day_retry"]["ledger_rows"], 1)
        self.assertEqual(report["moved_source"]["changed"], True)
        self.assertEqual(report["timezone"]["capture_offset"], "+07:00")
        self.assertEqual(report["network_used"], False)
        self.assertEqual(report["synthetic_only"], True)

    def test_commit_step_creates_a_commit_only_when_the_source_moves(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self._init_repository(root)
            sector = root / "sector.json"
            date = root / "date.json"
            sector.write_text(json.dumps(synthetic_sector_payload()), encoding="utf-8")
            date.write_text(json.dumps(synthetic_date_payload()), encoding="utf-8")
            self.assertEqual(self._run_capture(root).returncode, 0)
            self.assertTrue(self._commit_step(root))
            head = self._git(root, "rev-parse", "HEAD")
            self.assertEqual(self._run_capture(root).returncode, 0)
            self.assertFalse(self._commit_step(root), "unchanged source must produce no commit")
            self.assertEqual(self._git(root, "rev-parse", "HEAD"), head)
            moved = dict(SECTORS)
            moved["Protection - MHPSS"] = 6001
            sector.write_text(json.dumps(synthetic_sector_payload(moved)), encoding="utf-8")
            date.write_text(json.dumps(synthetic_date_payload(dt.date(2026, 9, 26))), encoding="utf-8")
            self.assertEqual(self._run_capture(root, capture_time="2026-09-28T09:00:00+07:00").returncode, 0)
            self.assertTrue(self._commit_step(root))
            self.assertNotEqual(self._git(root, "rev-parse", "HEAD"), head)

    def _init_repository(self, root: Path) -> None:
        for command in (
            ("init", "-q", "-b", "main"),
            ("config", "user.name", "test"),
            ("config", "user.email", "test@example.invalid"),
        ):
            self._git(root, *command)
        # The asset path is explicit and must already exist; the workflow makes it.
        (root / "data" / "ndrrma").mkdir(parents=True)

    def _git(self, root: Path, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            env={key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")},
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return completed.stdout.strip()

    def _run_capture(self, root: Path, capture_time: str = "2026-09-21T09:00:00+07:00"):
        return subprocess.run(
            [
                sys.executable,
                str(CAPTURE_SCRIPT),
                "--asset-dir",
                "data/ndrrma",
                "--sector-fixture",
                "sector.json",
                "--date-fixture",
                "date.json",
                "--capture-time",
                capture_time,
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )

    def _commit_step(self, root: Path) -> bool:
        """Replicate the workflow's guarded commit step; return whether it committed."""
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "data/ndrrma"], cwd=root, capture_output=True, text=True
        )
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        if not status.stdout.strip():
            return False
        self._git(root, "add", "--", "data/ndrrma")
        self._git(root, "commit", "-qm", "data: capture NDRRMA public aggregates")
        return True


class NdrrmaWorkflowContractTests(unittest.TestCase):
    def test_every_workflow_run_block_is_valid_bash(self) -> None:
        """A broken heredoc or quoting error in a `run:` block must fail here, not in CI."""
        text = WORKFLOW.read_text(encoding="utf-8")
        blocks = []
        lines = text.splitlines()
        index = 0
        while index < len(lines):
            stripped = lines[index].strip()
            if stripped in {"run: |", "run: >"}:
                body = []
                index += 1
                while index < len(lines) and (lines[index].startswith(" " * 10) or not lines[index].strip()):
                    body.append(lines[index][10:])
                    index += 1
                blocks.append("\n".join(body))
                continue
            if stripped.startswith("run: ") and not stripped.endswith("|"):
                blocks.append(" ".join(stripped[len("run: ") :].split()))
            index += 1
        self.assertGreaterEqual(len(blocks), 3)
        for number, block in enumerate(blocks):
            checked = subprocess.run(["bash", "-n"], input=block, text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, f"run block {number} is not valid bash: {checked.stderr}\n{block}")
            # No heredocs: an indented terminator silently swallowed the body of a
            # `python3 - <<'PY'` block here once, so validation lives in the script.
            self.assertNotIn("<<", block, f"run block {number} must not use a heredoc")
        # The workflow must never pass a test-only fixture flag to the real run.
        self.assertNotIn("--sector-fixture", text)
        self.assertNotIn("--date-fixture", text)

    def test_query_config_carries_only_public_embed_identifiers(self) -> None:
        config = json.loads(
            (REPOSITORY_ROOT / "config" / "ndrrma-powerbi-query.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["schema"], 1)
        self.assertEqual(
            config["api"],
            "https://wabi-north-europe-j-primary-api.analysis.windows.net"
            "/public/reports/querydata?synchronous=true",
        )
        self.assertEqual(set(config["sector_query"]["queries"][0]) >= {"Query"}, True)
        self.assertEqual(config["date_query"]["modelId"], config["sector_query"]["modelId"])
        # Public identifiers only: no account, token, password, or key material.
        for key in ("token", "password", "secret", "api_key", "authorization"):
            self.assertNotIn(key, json.dumps(config).casefold())

    def test_capture_is_stdlib_only_and_free_of_hermes_or_ai_dependencies(self) -> None:
        source = CAPTURE_SCRIPT.read_text(encoding="utf-8")
        imported = {
            match.group(1).split(".")[0]
            for match in re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", source, re.MULTILINE)
        }
        self.assertTrue(imported <= ALLOWED_STDLIB_IMPORTS, f"non-stdlib imports: {sorted(imported - ALLOWED_STDLIB_IMPORTS)}")
        for forbidden in (
            ".hermes",
            "mhpss_weekly_snapshot",
            "openai",
            "anthropic",
            "firebase",
            "requests",
            "service_account",
        ):
            self.assertNotIn(forbidden, source.casefold(), f"capture must not reference {forbidden!r}")

    def test_workflow_is_scheduled_dispatchable_pinned_and_least_privilege(self) -> None:
        self.assertTrue(WORKFLOW.exists(), f"workflow is missing: {WORKFLOW}")
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("schedule:", text)
        self.assertIn("cron: '15 2 * * 1'", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: write", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("python3 scripts/ndrrma_capture.py", text)
        self.assertIn("--asset-dir data/ndrrma --verify", text)
        self.assertIn("git status --porcelain -- data/ndrrma", text)
        self.assertNotIn("secrets.", text)
        uses_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("uses:")]
        self.assertGreaterEqual(len(uses_lines), 1)
        for line in uses_lines:
            reference = line.rsplit("@", 1)[1].split()[0]
            self.assertRegex(reference, r"^[0-9a-f]{40}$", f"action must be pinned to a full SHA: {line}")


if __name__ == "__main__":
    unittest.main()
