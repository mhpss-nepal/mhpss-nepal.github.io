#!/usr/bin/env python3
"""Conservative analytical reconciliation for synthetic referral records.

This module is a V2 review artifact. It emits data-quality candidates and count
views; it never edits or deletes canonical events and has no public publisher.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, Sequence

MATCH_EXACT = "REFERRAL_MATCH_EXACT"
POSSIBLE_MATCH_QUEUED = "REFERRAL_POSSIBLE_MATCH_QUEUED"
UNMATCHED_OUT = "REFERRAL_UNMATCHED_OUT"
UNMATCHED_IN = "REFERRAL_UNMATCHED_IN"
REFERRAL_DIRECTION_CONFLICT = "REFERRAL_DIRECTION_CONFLICT"
SAME_CODE_ATTRIBUTE_CONFLICT = "REFERRAL_SAME_CODE_ATTRIBUTE_CONFLICT"
MALFORMED_CODE = "REFERRAL_MALFORMED_CODE"
SMALL_CELL_SUGGESTION_SUPPRESSED = "REFERRAL_SMALL_CELL_SUGGESTION_SUPPRESSED"
CONTACT_CROSS_FORM_MATCH = "REFERRAL_CONTACT_CROSS_FORM_MATCH"

REFERRAL_PRIVACY_CLASS = "restricted-referral-person-list"
CONTACT_CODE_PATTERN = re.compile(r"^NP-[0-9A-Z]{5}-[0-9A-Z]{5}$")
DEFAULT_SMALL_CELL_THRESHOLD = 5
_CONTRADICTORY_FIELDS = ("sex", "age_band", "district")
_VALID_DIRECTIONS = {"IN", "OUT"}
_RULE_VERSIONS = {
    MATCH_EXACT: "referral-in-out/2.0-exact",
    POSSIBLE_MATCH_QUEUED: "referral-in-out/2.0-near-one-character",
    UNMATCHED_OUT: "referral-in-out/2.0-unmatched",
    UNMATCHED_IN: "referral-in-out/2.0-unmatched",
    REFERRAL_DIRECTION_CONFLICT: "referral-in-out/2.0-direction",
    SAME_CODE_ATTRIBUTE_CONFLICT: "referral-in-out/2.0-attributes",
    MALFORMED_CODE: "referral-in-out/2.0-format",
    SMALL_CELL_SUGGESTION_SUPPRESSED: "referral-in-out/2.0-small-cell",
    CONTACT_CROSS_FORM_MATCH: "referral-in-out/2.0-cross-form",
}


class ReconciliationError(ValueError):
    """The requested operation would violate the reconciliation contract."""


def reconcile_referrals(
    referrals: Iterable[Mapping[str, Any]],
    *,
    contacts: Iterable[Mapping[str, Any]] = (),
    small_cell_threshold: int = DEFAULT_SMALL_CELL_THRESHOLD,
) -> dict[str, Any]:
    """Return an analytical DQ view without mutating source records.

    Exact equal-code IN/OUT pairs count as one only when there is exactly one of
    each and their shared attributes do not contradict. Near-code candidates
    are review signals, never automatic identity. Suggestions are suppressed in
    cells with fewer than ``small_cell_threshold`` distinct valid codes.
    """
    if type(small_cell_threshold) is not int or small_cell_threshold != DEFAULT_SMALL_CELL_THRESHOLD:
        raise ReconciliationError(
            f"small-cell threshold is fixed policy at {DEFAULT_SMALL_CELL_THRESHOLD}"
        )

    rows = [_normalize(record, expected_kind="referral") for record in referrals]
    contact_rows = [_normalize(record, expected_kind="service_contact") for record in contacts]
    event_ids = [row["event_id"] for row in rows + contact_rows]
    if len(event_ids) != len(set(event_ids)):
        raise ReconciliationError("duplicate event_id in verified projection input")
    items: list[dict[str, Any]] = []
    used: set[str] = set()

    valid_rows: list[dict[str, Any]] = []
    for row in rows:
        if not CONTACT_CODE_PATTERN.fullmatch(row["contact_code"]):
            items.append(_item(MALFORMED_CODE, [row], status="open", auto_merged=False))
            used.add(row["event_id"])
        elif row["direction"] not in _VALID_DIRECTIONS:
            items.append(_item(REFERRAL_DIRECTION_CONFLICT, [row], status="open", auto_merged=False))
            used.add(row["event_id"])
        else:
            valid_rows.append(row)

    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in valid_rows:
        by_code[row["contact_code"]].append(row)

    for code in sorted(by_code):
        group = sorted(by_code[code], key=lambda row: row["event_id"])
        directions = Counter(row["direction"] for row in group)
        if len(group) == 2 and directions == Counter({"IN": 1, "OUT": 1}):
            contradictions = _contradictions(group[0], group[1])
            if contradictions:
                items.append(_item(
                    SAME_CODE_ATTRIBUTE_CONFLICT,
                    group,
                    status="open",
                    auto_merged=False,
                    conflicting_fields=contradictions,
                ))
            else:
                items.append(_item(MATCH_EXACT, group, status="resolved_by_rule", auto_merged=False))
            used.update(row["event_id"] for row in group)
        elif len(group) > 1:
            items.append(_item(
                REFERRAL_DIRECTION_CONFLICT,
                group,
                status="open",
                auto_merged=False,
                direction_counts=dict(sorted(directions.items())),
            ))
            used.update(row["event_id"] for row in group)

    unmatched = [row for row in valid_rows if row["event_id"] not in used]
    distinct_codes_by_cell: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in valid_rows:
        distinct_codes_by_cell[_cell(row)].add(row["contact_code"])

    candidate_rows: set[str] = set()
    for left_index, left in enumerate(unmatched):
        for right in unmatched[left_index + 1:]:
            if left["direction"] == right["direction"] or _cell(left) != _cell(right):
                continue
            if _code_distance(left["contact_code"], right["contact_code"]) != 1:
                continue
            pair = sorted([left, right], key=lambda row: row["event_id"])
            candidate_rows.update(row["event_id"] for row in pair)
            missing_cell = not all(_cell(left))
            if missing_cell or len(distinct_codes_by_cell[_cell(left)]) < small_cell_threshold:
                items.append(_item(
                    SMALL_CELL_SUGGESTION_SUPPRESSED,
                    pair,
                    status="suppressed",
                    auto_merged=False,
                    cell_size=len(distinct_codes_by_cell[_cell(left)]),
                    threshold=small_cell_threshold,
                    missing_cell=missing_cell,
                    expose_codes=False,
                ))
            else:
                items.append(_item(
                    POSSIBLE_MATCH_QUEUED,
                    pair,
                    status="open",
                    auto_merged=False,
                    comparison_basis="contact_code_hamming_distance_1_only",
                ))

    for row in unmatched:
        code = UNMATCHED_OUT if row["direction"] == "OUT" else UNMATCHED_IN
        suppress_code = any(
            item["code"] == SMALL_CELL_SUGGESTION_SUPPRESSED
            and row["event_id"] in item["record_ids"]
            for item in items
        )
        items.append(_item(
            code,
            [row],
            status="open_data_quality_signal" if row["event_id"] in candidate_rows else "unmatched",
            auto_merged=False,
            expose_codes=not suppress_code,
        ))

    items.extend(_cross_form_items(valid_rows, contact_rows))
    items.sort(key=lambda item: (item["code"], item["dq_key"]))
    return {
        "contract": "mhpss.referral-reconciliation/2.0-review",
        "operation": "analytical_data_quality_only",
        "privacy_class": REFERRAL_PRIVACY_CLASS,
        "canonical_mutation": False,
        "items": items,
        "counts": _counts(rows, items),
        "publication": {
            "public_stats_allowed": False,
            "reason": "A referral collection is a restricted list of referred persons.",
            "allowed_outputs": ["restricted_internal_dq", "restricted_internal_aggregate"],
        },
        "limitations": {
            "contact_code_is_pseudonym_not_anonymous": True,
            "server_held_secret_present": False,
            "definitive_deduplication_claim_allowed": False,
            "small_cell_threshold": small_cell_threshold,
        },
    }


def _normalize(record: Mapping[str, Any], *, expected_kind: str) -> dict[str, Any]:
    value = dict(record)
    event_id = value.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ReconciliationError("every record requires a non-empty event_id")
    if value.get("kind") != expected_kind:
        raise ReconciliationError(f"expected kind {expected_kind}")
    code = value.get("contact_code")
    if not isinstance(code, str):
        code = ""
    elif code != code.strip().upper():
        raise ReconciliationError("noncanonical contact_code; correct through a V2 event")
    value["event_id"] = event_id.strip()
    value["contact_code"] = code
    direction = value.get("direction", "")
    if direction and (not isinstance(direction, str) or direction != direction.strip().upper()):
        raise ReconciliationError("noncanonical direction; correct through a V2 event")
    value["direction"] = direction
    return value


def _cell(record: Mapping[str, Any]) -> tuple[str, str]:
    return (str(record.get("district", "")), str(record.get("site_from", "")))


def _code_distance(left: str, right: str) -> int:
    if len(left) != len(right):
        return max(len(left), len(right))
    return sum(a != b for a, b in zip(left, right))


def _contradictions(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
    return [
        field for field in _CONTRADICTORY_FIELDS
        if left.get(field) not in (None, "")
        and right.get(field) not in (None, "")
        and left.get(field) != right.get(field)
    ]


def _item(
    code: str,
    records: Sequence[Mapping[str, Any]],
    *,
    status: str,
    auto_merged: bool,
    expose_codes: bool = True,
    **details: Any,
) -> dict[str, Any]:
    record_ids = sorted(str(record["event_id"]) for record in records)
    key_material = json.dumps(
        {"code": code, "record_ids": record_ids},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    value: dict[str, Any] = {
        "dq_key": f"{code}|{hashlib.sha256(key_material).hexdigest()}",
        "code": code,
        "record_ids": record_ids,
        "source_forms": sorted({str(record["kind"]) for record in records}),
        "status": status,
        "auto_merged": auto_merged,
        "rule_version": _RULE_VERSIONS[code],
        "directions": sorted({str(record.get("direction", "")) for record in records if record.get("direction")}),
        "review_attributes": [
            {
                "record_id": str(record["event_id"]),
                "sex": record.get("sex", ""),
                "age_band": record.get("age_band", ""),
                "district": record.get("district", ""),
                "site": record.get("site_from", record.get("site", "")),
            }
            for record in records
        ],
    }
    if expose_codes:
        value["contact_codes"] = sorted({str(record["contact_code"]) for record in records})
    value.update(details)
    value["evidence_digest"] = hashlib.sha256(
        json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return value


def _cross_form_items(
    referrals: list[dict[str, Any]], contacts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for contact_row in contacts:
        if CONTACT_CODE_PATTERN.fullmatch(contact_row["contact_code"]):
            by_code[contact_row["contact_code"]].append(contact_row)
    items: list[dict[str, Any]] = []
    for referral_row in referrals:
        for contact_row in by_code.get(referral_row["contact_code"], []):
            contradictions = _contradictions(referral_row, contact_row)
            if contradictions:
                items.append(_item(
                    SAME_CODE_ATTRIBUTE_CONFLICT,
                    [referral_row, contact_row],
                    status="open",
                    auto_merged=False,
                    conflicting_fields=contradictions,
                    cross_form=True,
                ))
            else:
                items.append(_item(
                    CONTACT_CROSS_FORM_MATCH,
                    [referral_row, contact_row],
                    status="informational",
                    auto_merged=False,
                    cross_form=True,
                ))
    return items


def _counts(rows: list[dict[str, Any]], items: list[dict[str, Any]]) -> dict[str, int]:
    exact_pairs = sum(item["code"] == MATCH_EXACT for item in items)
    return {
        "raw_referral_records": len(rows),
        # Conservative analytical count: only an unambiguous exact pair reduces
        # two referral records to one person. Review candidates remain separate.
        "internal_referral_persons_resolved": len(rows) - exact_pairs,
        "exact_pairs": exact_pairs,
        "possible_duplicate_pairs_open": sum(
            item["code"] == POSSIBLE_MATCH_QUEUED for item in items
        ),
        "small_cell_suggestions_suppressed": sum(
            item["code"] == SMALL_CELL_SUGGESTION_SUPPRESSED for item in items
        ),
        "unmatched_out": sum(item["code"] == UNMATCHED_OUT for item in items),
        "unmatched_in": sum(item["code"] == UNMATCHED_IN for item in items),
        "malformed_code_records": sum(item["code"] == MALFORMED_CODE for item in items),
        "open_conflicts": sum(
            item["code"] in {REFERRAL_DIRECTION_CONFLICT, SAME_CODE_ATTRIBUTE_CONFLICT}
            for item in items
        ),
    }
