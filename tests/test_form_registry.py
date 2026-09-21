#!/usr/bin/env python3
"""Failing-first tests for the V1/V2 form registry review artifact.

Synthetic metadata only. The prototype validates declarations and generates a
landing-page fixture; it does not modify the live Form or Hub pages.
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "packages" / "form_registry"
sys.path.insert(0, str(MODULE))

from form_registry import (  # noqa: E402
    RegistryError,
    load_registry,
    publication_allowed,
    render_landing_fixture,
    validate_registry,
)

REGISTRY_PATH = ROOT / "config" / "form-registry.yaml"


class FormRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_registry(REGISTRY_PATH)

    def test_repository_registry_is_valid_and_declares_every_current_kind(self) -> None:
        validate_registry(self.registry, ROOT)
        forms = self.registry["forms"]
        self.assertEqual(
            {entry["kind"] for entry in forms},
            {"activity", "service_contact", "referral", "phq9", "self_report"},
        )

    def test_a_form_without_a_reading_home_fails_closed(self) -> None:
        broken = copy.deepcopy(self.registry)
        broken["forms"][0]["reading_home"] = ""

        with self.assertRaisesRegex(RegistryError, "reading_home"):
            validate_registry(broken, ROOT)

    def test_a_form_with_a_nonexistent_reading_home_fails_closed(self) -> None:
        broken = copy.deepcopy(self.registry)
        broken["forms"][0]["reading_home"] = "hub.missing-section"

        with self.assertRaisesRegex(RegistryError, "unknown reading_home"):
            validate_registry(broken, ROOT)

    def test_clinical_and_safeguarding_classes_can_never_publish(self) -> None:
        by_kind = {entry["kind"]: entry for entry in self.registry["forms"]}
        for kind in ("phq9", "referral"):
            with self.subTest(kind=kind):
                self.assertFalse(publication_allowed(by_kind[kind], "public_stats"))

    def test_coordination_publication_uses_a_named_rule_gated_route(self) -> None:
        activity = next(entry for entry in self.registry["forms"] if entry["kind"] == "activity")
        self.assertTrue(publication_allowed(activity, "public_stats"))
        self.assertEqual(activity["public_output"]["route"], "rule-gated-aggregate")
        self.assertEqual(
            set(activity["public_output"]["documents"]),
            {"flood_response", "coordination_full"},
        )

    def test_a_form_cannot_invent_its_own_public_document(self) -> None:
        broken = copy.deepcopy(self.registry)
        activity = next(entry for entry in broken["forms"] if entry["kind"] == "activity")
        activity["public_output"]["documents"] = ["phq9_scored_items"]

        with self.assertRaisesRegex(RegistryError, "not an approved public document"):
            validate_registry(broken, ROOT)

    def test_a_form_cannot_route_to_a_home_that_does_not_accept_its_kind(self) -> None:
        broken = copy.deepcopy(self.registry)
        activity = next(entry for entry in broken["forms"] if entry["kind"] == "activity")
        activity["reading_home"] = "hub.forms.contact"

        with self.assertRaisesRegex(RegistryError, "does not accept kind"):
            validate_registry(broken, ROOT)

    def test_a_form_cannot_declare_direct_canonical_writes_or_its_own_identity(self) -> None:
        for forbidden in (
            {"canonical_write": "browser-direct"},
            {"event_id_source": "form"},
            {"stream_id_source": "form"},
        ):
            broken = copy.deepcopy(self.registry)
            broken["forms"][0].update(forbidden)
            with self.subTest(forbidden=forbidden):
                with self.assertRaisesRegex(RegistryError, "forbidden field"):
                    validate_registry(broken, ROOT)

    def test_generated_landing_fixture_contains_only_trial_visible_forms(self) -> None:
        rendered = render_landing_fixture(self.registry)
        expected = [
            entry for entry in self.registry["forms"]
            if entry["trial_status"] == "approved-for-trial" and entry["field_landing"]
        ]
        self.assertEqual(rendered.count('class="form-card"'), len(expected))
        for entry in expected:
            self.assertIn(entry["file_path"], rendered)
            self.assertIn(entry["title"], rendered)
        for entry in self.registry["forms"]:
            if entry not in expected:
                self.assertNotIn(f'href="{entry["file_path"]}"', rendered)

    def test_retired_form_keeps_kind_and_version_history_resolvable(self) -> None:
        retired = copy.deepcopy(self.registry)
        retired["forms"][0]["trial_status"] = "retired"
        retired["forms"][0]["field_landing"] = False

        validate_registry(retired, ROOT)
        entry = retired["forms"][0]
        self.assertTrue(entry["schema_versions"])
        self.assertTrue(entry["reading_home"])
        self.assertNotIn(entry["file_path"], render_landing_fixture(retired))


if __name__ == "__main__":
    unittest.main()
