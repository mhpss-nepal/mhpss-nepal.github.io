#!/usr/bin/env python3
"""Failing-first tests for conservative referral IN/OUT reconciliation.

Synthetic records only. These tests exercise an analytical DQ projection; they
must never mutate, delete, or publish the canonical referral records.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "packages" / "referral_reconciliation"
sys.path.insert(0, str(MODULE))

from referral_reconciliation import (  # noqa: E402
    MALFORMED_CODE,
    MATCH_EXACT,
    POSSIBLE_MATCH_QUEUED,
    REFERRAL_DIRECTION_CONFLICT,
    REFERRAL_PRIVACY_CLASS,
    SAME_CODE_ATTRIBUTE_CONFLICT,
    SMALL_CELL_SUGGESTION_SUPPRESSED,
    UNMATCHED_IN,
    UNMATCHED_OUT,
    ReconciliationError,
    reconcile_referrals,
)


def referral(event_id: str, code: str, direction: str, **changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "event_id": event_id,
        "kind": "referral",
        "contact_code": code,
        "direction": direction,
        "district": "RAS",
        "site_from": "SITE-A",
        "sex": "F",
        "age_band": "25-59",
        "date_ad": "2026-09-20",
    }
    value.update(changes)
    return value


def contact(event_id: str, code: str, **changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "event_id": event_id,
        "kind": "service_contact",
        "contact_code": code,
        "district": "RAS",
        "site": "SITE-A",
        "sex": "F",
        "age_band": "25-59",
    }
    value.update(changes)
    return value


def filler(index: int) -> dict[str, object]:
    # Distinct valid codes in the same comparison cell make near-match review
    # eligible without introducing another opposite-direction candidate.
    return referral(f"fill-{index}", f"NP-ZZZZ{index}-YYYY{index}", "OUT")


class ReferralReconciliationTests(unittest.TestCase):
    def test_exact_opposite_direction_pair_counts_one_person_without_mutation(self) -> None:
        records = [
            referral("out-1", "NP-ABCDE-12345", "OUT"),
            referral("in-1", "NP-ABCDE-12345", "IN"),
        ]
        snapshot = [dict(item) for item in records]

        result = reconcile_referrals(records)

        self.assertEqual(records, snapshot)
        self.assertEqual(result["counts"]["internal_referral_persons_resolved"], 1)
        self.assertEqual(result["counts"]["raw_referral_records"], 2)
        self.assertEqual(result["items"][0]["code"], MATCH_EXACT)
        self.assertEqual(result["items"][0]["record_ids"], ["in-1", "out-1"])

    def test_near_match_is_queued_and_never_auto_merged(self) -> None:
        records = [
            referral("out-1", "NP-ABCDE-12345", "OUT"),
            referral("in-1", "NP-ABCDF-12345", "IN"),
            *[filler(index) for index in range(5)],
        ]

        result = reconcile_referrals(records, small_cell_threshold=5)

        possible = [item for item in result["items"] if item["code"] == POSSIBLE_MATCH_QUEUED]
        self.assertEqual(len(possible), 1)
        self.assertEqual(possible[0]["record_ids"], ["in-1", "out-1"])
        self.assertFalse(possible[0]["auto_merged"])
        self.assertEqual(result["counts"]["internal_referral_persons_resolved"], 7)
        self.assertEqual(result["counts"]["possible_duplicate_pairs_open"], 1)

    def test_lone_out_and_lone_in_each_remain_one_unmatched_person(self) -> None:
        result = reconcile_referrals([
            referral("out-1", "NP-ABCDE-12345", "OUT"),
            referral("in-1", "NP-ZYXWV-98765", "IN"),
        ])

        self.assertEqual({item["code"] for item in result["items"]}, {UNMATCHED_OUT, UNMATCHED_IN})
        self.assertEqual(result["counts"]["internal_referral_persons_resolved"], 2)
        self.assertEqual(result["counts"]["unmatched_out"], 1)
        self.assertEqual(result["counts"]["unmatched_in"], 1)

    def test_same_code_contradictory_attributes_never_matches(self) -> None:
        result = reconcile_referrals([
            referral("out-1", "NP-ABCDE-12345", "OUT", sex="F"),
            referral("in-1", "NP-ABCDE-12345", "IN", sex="M"),
        ])

        self.assertEqual(result["items"][0]["code"], SAME_CODE_ATTRIBUTE_CONFLICT)
        self.assertFalse(result["items"][0]["auto_merged"])
        self.assertEqual(result["counts"]["internal_referral_persons_resolved"], 2)

    def test_same_code_same_direction_is_a_direction_conflict(self) -> None:
        result = reconcile_referrals([
            referral("out-1", "NP-ABCDE-12345", "OUT"),
            referral("out-2", "NP-ABCDE-12345", "OUT"),
        ])

        self.assertEqual(result["items"][0]["code"], REFERRAL_DIRECTION_CONFLICT)
        self.assertEqual(result["counts"]["internal_referral_persons_resolved"], 2)

    def test_malformed_code_is_separate_and_never_suggested(self) -> None:
        result = reconcile_referrals([
            referral("bad-1", "NP-NOT-VALID", "OUT"),
            referral("in-1", "NP-ABCDE-12345", "IN"),
        ])

        self.assertIn(MALFORMED_CODE, {item["code"] for item in result["items"]})
        self.assertEqual(result["counts"]["malformed_code_records"], 1)
        self.assertEqual(result["counts"]["internal_referral_persons_resolved"], 2)

    def test_small_cell_suppresses_near_match_suggestion(self) -> None:
        result = reconcile_referrals([
            referral("out-1", "NP-ABCDE-12345", "OUT"),
            referral("in-1", "NP-ABCDF-12345", "IN"),
        ], small_cell_threshold=5)

        self.assertNotIn(POSSIBLE_MATCH_QUEUED, {item["code"] for item in result["items"]})
        suppressed = [item for item in result["items"] if item["code"] == SMALL_CELL_SUGGESTION_SUPPRESSED]
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["record_ids"], ["in-1", "out-1"])
        self.assertNotIn("contact_codes", suppressed[0])
        serialized = str(result)
        self.assertNotIn("NP-ABCDE-12345", serialized)
        self.assertNotIn("NP-ABCDF-12345", serialized)

    def test_small_cell_policy_cannot_be_weakened_and_missing_cell_is_suppressed(self) -> None:
        with self.assertRaisesRegex(ReconciliationError, "fixed policy"):
            reconcile_referrals([], small_cell_threshold=1)
        result = reconcile_referrals([
            referral("out-1", "NP-ABCDE-12345", "OUT", district="", site_from=""),
            referral("in-1", "NP-ABCDF-12345", "IN", district="", site_from=""),
            *[filler(index) for index in range(5)],
        ])
        self.assertIn(
            SMALL_CELL_SUGGESTION_SUPPRESSED,
            {item["code"] for item in result["items"]},
        )

    def test_noncanonical_values_and_duplicate_event_ids_fail_closed(self) -> None:
        with self.assertRaisesRegex(ReconciliationError, "noncanonical contact_code"):
            reconcile_referrals([referral("out-1", " np-abcde-12345 ", "OUT")])
        with self.assertRaisesRegex(ReconciliationError, "noncanonical direction"):
            reconcile_referrals([referral("out-1", "NP-ABCDE-12345", "out")])
        with self.assertRaisesRegex(ReconciliationError, "duplicate event_id"):
            reconcile_referrals([
                referral("same-id", "NP-ABCDE-12345", "OUT"),
                referral("same-id", "NP-ABCDE-12345", "IN"),
            ])

    def test_referral_class_is_marked_for_sink_enforcement(self) -> None:
        result = reconcile_referrals([
            referral("out-1", "NP-ABCDE-12345", "OUT"),
            referral("in-1", "NP-ABCDE-12345", "IN"),
        ])

        self.assertEqual(REFERRAL_PRIVACY_CLASS, "restricted-referral-person-list")
        self.assertFalse(result["publication"]["public_stats_allowed"])

    def test_contact_form_cross_check_flags_disagreement_but_never_changes_count(self) -> None:
        records = [referral("out-1", "NP-ABCDE-12345", "OUT")]
        result = reconcile_referrals(records, contacts=[
            contact("contact-1", "NP-ABCDE-12345", age_band="60+")
        ])

        conflicts = [item for item in result["items"] if item["code"] == SAME_CODE_ATTRIBUTE_CONFLICT]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["source_forms"], ["referral", "service_contact"])
        self.assertEqual(result["counts"]["internal_referral_persons_resolved"], 1)

if __name__ == "__main__":
    unittest.main()
