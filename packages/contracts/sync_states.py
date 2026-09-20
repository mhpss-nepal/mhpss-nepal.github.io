#!/usr/bin/env python3
"""Explicit V2 sync state machine and frontend wording."""

from __future__ import annotations

CREATED = "created_memory_only"
DURABLE_QUEUED = "durable_queued"
IN_FLIGHT = "in_flight"
RETRYABLE = "retryable_failure"
ACKNOWLEDGED = "server_acknowledged"
CONFLICT = "conflict_recovery_required"
PROJECTED = "projected_reconciled"
REVIEWED = "reviewed_accepted"

_TRANSITIONS = {
    (CREATED, "durable_transaction_committed"): DURABLE_QUEUED,
    (DURABLE_QUEUED, "transmission_started"): IN_FLIGHT,
    (RETRYABLE, "transmission_started"): IN_FLIGHT,
    (IN_FLIGHT, "retryable_failure"): RETRYABLE,
    (IN_FLIGHT, "ack_mismatch"): CONFLICT,
    (IN_FLIGHT, "exact_ack_read_back"): ACKNOWLEDGED,
    (ACKNOWLEDGED, "projection_reconciled"): PROJECTED,
    (PROJECTED, "review_recorded"): REVIEWED,
}

_MESSAGES = {
    CREATED: "Not saved. Keep this page open and export a recovery copy if a warning appears.",
    DURABLE_QUEUED: "Saved on this device and queued. Server acknowledgement is pending.",
    IN_FLIGHT: "Sending the saved event. Server acknowledgement is pending.",
    RETRYABLE: "Still queued on this device after a retryable failure. Do not resubmit or clear storage.",
    ACKNOWLEDGED: "Received by the server for this exact event revision. Dashboard inclusion is not yet confirmed.",
    CONFLICT: "Conflict: the exact event was not acknowledged. Do not resubmit or clear storage; export recovery evidence.",
    PROJECTED: "Included in the reconciled dashboard projection. Review status is not yet recorded.",
    REVIEWED: "Reviewed and accepted under the recorded review decision.",
}

ALL_STATES = frozenset(_MESSAGES)


class InvalidTransition(ValueError):
    """A sync event attempted to skip an evidence boundary."""


def transition(state: str, event: str) -> str:
    try:
        return _TRANSITIONS[(state, event)]
    except KeyError as error:
        raise InvalidTransition(f"invalid sync transition: {state} + {event}") from error


def user_message(state: str) -> str:
    try:
        return _MESSAGES[state]
    except KeyError as error:
        raise ValueError(f"unknown sync state: {state}") from error
