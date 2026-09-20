#!/usr/bin/env python3
"""Explicit sync-state and truthful frontend wording contracts."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "contracts"))

from sync_states import (  # noqa: E402
    ACKNOWLEDGED,
    ALL_STATES,
    CONFLICT,
    CREATED,
    DURABLE_QUEUED,
    IN_FLIGHT,
    PROJECTED,
    REVIEWED,
    RETRYABLE,
    InvalidTransition,
    transition,
    user_message,
)


class SyncStateTests(unittest.TestCase):
    def test_state_vocabulary_is_complete_and_unique(self) -> None:
        self.assertEqual(
            ALL_STATES,
            {CREATED, DURABLE_QUEUED, IN_FLIGHT, RETRYABLE, ACKNOWLEDGED, CONFLICT, PROJECTED, REVIEWED},
        )

    def test_happy_path_keeps_persistence_delivery_projection_and_review_distinct(self) -> None:
        state = CREATED
        state = transition(state, "durable_transaction_committed")
        self.assertEqual(state, DURABLE_QUEUED)
        self.assertIn("saved on this device", user_message(state).lower())
        self.assertNotIn("received", user_message(state).lower())

        state = transition(state, "transmission_started")
        self.assertEqual(state, IN_FLIGHT)
        self.assertNotIn("received", user_message(state).lower())

        state = transition(state, "exact_ack_read_back")
        self.assertEqual(state, ACKNOWLEDGED)
        self.assertIn("received", user_message(state).lower())
        self.assertNotIn("included in the dashboard", user_message(state).lower())

        state = transition(state, "projection_reconciled")
        self.assertEqual(state, PROJECTED)
        self.assertIn("dashboard", user_message(state).lower())
        self.assertNotIn("reviewed and accepted", user_message(state).lower())

        state = transition(state, "review_recorded")
        self.assertEqual(state, REVIEWED)
        self.assertIn("reviewed", user_message(state).lower())

    def test_retry_never_claims_receipt_and_reuses_the_durable_obligation(self) -> None:
        state = transition(CREATED, "durable_transaction_committed")
        state = transition(state, "transmission_started")
        state = transition(state, "retryable_failure")
        self.assertEqual(state, RETRYABLE)
        self.assertIn("still queued", user_message(state).lower())
        self.assertNotIn("received", user_message(state).lower())
        self.assertEqual(transition(state, "transmission_started"), IN_FLIGHT)

    def test_ack_mismatch_is_a_conflict_not_success(self) -> None:
        state = transition(CREATED, "durable_transaction_committed")
        state = transition(state, "transmission_started")
        state = transition(state, "ack_mismatch")
        self.assertEqual(state, CONFLICT)
        self.assertIn("do not resubmit", user_message(state).lower())
        self.assertNotIn("received", user_message(state).lower())

    def test_illegal_shortcuts_fail_closed(self) -> None:
        illegal = (
            (CREATED, "exact_ack_read_back"),
            (DURABLE_QUEUED, "projection_reconciled"),
            (IN_FLIGHT, "projection_reconciled"),
            (ACKNOWLEDGED, "review_recorded"),
            (PROJECTED, "transmission_started"),
        )
        for state, event in illegal:
            with self.subTest(state=state, event=event):
                with self.assertRaises(InvalidTransition):
                    transition(state, event)


if __name__ == "__main__":
    unittest.main()
