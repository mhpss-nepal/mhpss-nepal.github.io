#!/usr/bin/env python3
"""Validate and render the MHPSS form registry review artifact.

The repository intentionally has no third-party runtime dependency, so the
loader implements the small YAML subset used by config/form-registry.yaml.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Any


class RegistryError(ValueError):
    """A form declaration fails closed."""


ALLOWED_TRIAL_STATUS = {"approved-for-trial", "dummy", "retired"}
ALLOWED_PRIVACY_CLASSES = {
    "coordination-aggregate",
    "clinical",
    "safeguarding",
    "anonymous-free-text",
    "restricted-person-record",
}
ALLOWED_PUBLIC_ROUTES = {"never", "rule-gated-aggregate"}
FORBIDDEN_FORM_FIELDS = {"canonical_write", "event_id_source", "stream_id_source"}
REQUIRED_FORM_FIELDS = {
    "id",
    "file_path",
    "kind",
    "title",
    "trial_status",
    "field_landing",
    "reading_home",
    "privacy_class",
    "schema_versions",
    "public_output",
}
REQUIRED_HOME_FIELDS = {"path", "selector", "url", "accepted_kinds"}


def _scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return {}
    if value == "[]":
        return []
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "null":
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _meaningful_lines(text: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if "\t" in raw:
            raise RegistryError(f"line {number}: tabs are not allowed")
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise RegistryError(f"line {number}: indentation must use two-space steps")
        result.append((indent, raw.strip()))
    return result


def _split_mapping(text: str, line_number: int) -> tuple[str, str]:
    if ":" not in text:
        raise RegistryError(f"line {line_number}: expected key: value")
    key, value = text.split(":", 1)
    key = key.strip()
    if not key:
        raise RegistryError(f"line {line_number}: empty key")
    return key, value.strip()


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines) or lines[index][0] != indent:
        raise RegistryError("invalid YAML block")
    is_list = lines[index][1].startswith("- ") or lines[index][1] == "-"
    container: Any = [] if is_list else {}
    while index < len(lines):
        current_indent, text = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise RegistryError(f"unexpected indentation near: {text}")
        if is_list:
            if not text.startswith("-"):
                raise RegistryError(f"mixed list and mapping near: {text}")
            item_text = text[1:].strip()
            if not item_text:
                if index + 1 >= len(lines) or lines[index + 1][0] <= indent:
                    raise RegistryError("empty list item")
                value, index = _parse_block(lines, index + 1, lines[index + 1][0])
                container.append(value)
                continue
            if ":" in item_text:
                key, raw_value = _split_mapping(item_text, index + 1)
                item: dict[str, Any] = {key: _scalar(raw_value)}
                index += 1
                while index < len(lines) and lines[index][0] > indent:
                    child_indent, child_text = lines[index]
                    if child_indent != indent + 2 or child_text.startswith("-"):
                        raise RegistryError(f"invalid list mapping near: {child_text}")
                    child_key, child_raw = _split_mapping(child_text, index + 1)
                    if child_raw:
                        item[child_key] = _scalar(child_raw)
                        index += 1
                    else:
                        if index + 1 >= len(lines) or lines[index + 1][0] <= child_indent:
                            item[child_key] = {}
                            index += 1
                        else:
                            child_value, index = _parse_block(lines, index + 1, lines[index + 1][0])
                            item[child_key] = child_value
                container.append(item)
                continue
            container.append(_scalar(item_text))
            index += 1
            continue
        if text.startswith("-"):
            raise RegistryError(f"mixed mapping and list near: {text}")
        key, raw_value = _split_mapping(text, index + 1)
        if key in container:
            raise RegistryError(f"duplicate key: {key}")
        if raw_value:
            container[key] = _scalar(raw_value)
            index += 1
        else:
            if index + 1 >= len(lines) or lines[index + 1][0] <= indent:
                container[key] = {}
                index += 1
            else:
                value, index = _parse_block(lines, index + 1, lines[index + 1][0])
                container[key] = value
    return container, index


def load_registry(path: Path) -> dict[str, Any]:
    lines = _meaningful_lines(path.read_text(encoding="utf-8"))
    if not lines:
        raise RegistryError("registry is empty")
    parsed, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines) or not isinstance(parsed, dict):
        raise RegistryError("registry root must be a mapping")
    return parsed


def _require_nonempty_string(entry: dict[str, Any], field: str, form_id: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"form {form_id}: {field} must be a non-empty string")
    return value


def _anchor_exists(source: str, selector: str) -> bool:
    return selector in source


def validate_registry(registry: dict[str, Any], root: Path) -> None:
    if registry.get("registry_version") != "mhpss.form-registry/0.1.0":
        raise RegistryError("unsupported registry_version")
    policy = registry.get("policy")
    homes = registry.get("homes")
    forms = registry.get("forms")
    if not isinstance(policy, dict) or not isinstance(homes, dict) or not isinstance(forms, list):
        raise RegistryError("policy, homes, and forms are required")
    publishable = set(policy.get("publishable_privacy_classes", []))
    never_publish = set(policy.get("never_publish_privacy_classes", []))
    public_documents = policy.get("public_documents")
    if not isinstance(public_documents, list) or not public_documents or not all(
        isinstance(x, str) and x for x in public_documents
    ):
        raise RegistryError("policy.public_documents is required")
    if policy.get("public_sink") != "public_stats":
        raise RegistryError("registry must bind the public_stats sink")
    if publishable & never_publish:
        raise RegistryError("privacy classes cannot be both publishable and never-publish")
    if not publishable <= ALLOWED_PRIVACY_CLASSES or not never_publish <= ALLOWED_PRIVACY_CLASSES:
        raise RegistryError("unknown policy privacy class")
    if policy.get("v2_contract") != "mhpss.event/2.0":
        raise RegistryError("registry must bind the approved V2 contract")

    checked_homes: dict[str, dict[str, Any]] = {}
    for home_id, home in homes.items():
        if not isinstance(home, dict):
            raise RegistryError(f"home {home_id}: declaration must be a mapping")
        missing_home = REQUIRED_HOME_FIELDS - home.keys()
        if missing_home:
            raise RegistryError(f"home {home_id}: missing field {sorted(missing_home)[0]}")
        path = root / _require_nonempty_string(home, "path", home_id)
        selector = _require_nonempty_string(home, "selector", home_id)
        _require_nonempty_string(home, "url", home_id)
        accepted = home.get("accepted_kinds")
        if not path.is_file():
            raise RegistryError(f"home {home_id}: path does not exist")
        source = path.read_text(encoding="utf-8")
        if not _anchor_exists(source, selector):
            raise RegistryError(f"home {home_id}: selector {selector} does not exist")
        if not isinstance(accepted, list) or not accepted or not all(isinstance(x, str) for x in accepted):
            raise RegistryError(f"home {home_id}: accepted_kinds is required")
        checked_homes[home_id] = home

    seen_ids: set[str] = set()
    seen_kinds: set[str] = set()
    seen_paths: set[str] = set()
    for raw_entry in forms:
        if not isinstance(raw_entry, dict):
            raise RegistryError("every form entry must be a mapping")
        form_id = str(raw_entry.get("id") or "<unknown>")
        forbidden = FORBIDDEN_FORM_FIELDS & raw_entry.keys()
        if forbidden:
            raise RegistryError(f"form {form_id}: forbidden field {sorted(forbidden)[0]}")
        missing = REQUIRED_FORM_FIELDS - raw_entry.keys()
        if missing:
            raise RegistryError(f"form {form_id}: missing field {sorted(missing)[0]}")
        form_id = _require_nonempty_string(raw_entry, "id", form_id)
        path_value = _require_nonempty_string(raw_entry, "file_path", form_id)
        kind = _require_nonempty_string(raw_entry, "kind", form_id)
        _require_nonempty_string(raw_entry, "title", form_id)
        home_id = _require_nonempty_string(raw_entry, "reading_home", form_id)
        privacy_class = _require_nonempty_string(raw_entry, "privacy_class", form_id)
        if form_id in seen_ids or kind in seen_kinds or path_value in seen_paths:
            raise RegistryError(f"form {form_id}: id, kind, and file_path must be unique")
        seen_ids.add(form_id)
        seen_kinds.add(kind)
        seen_paths.add(path_value)
        if not (root / path_value).is_file():
            raise RegistryError(f"form {form_id}: file_path does not exist")
        if raw_entry.get("trial_status") not in ALLOWED_TRIAL_STATUS:
            raise RegistryError(f"form {form_id}: invalid trial_status")
        if not isinstance(raw_entry.get("field_landing"), bool):
            raise RegistryError(f"form {form_id}: field_landing must be boolean")
        if home_id not in checked_homes:
            raise RegistryError(f"form {form_id}: unknown reading_home {home_id}")
        if kind not in checked_homes[home_id]["accepted_kinds"]:
            raise RegistryError(f"form {form_id}: reading_home does not accept kind {kind}")
        if privacy_class not in ALLOWED_PRIVACY_CLASSES:
            raise RegistryError(f"form {form_id}: invalid privacy_class")
        schema_versions = raw_entry.get("schema_versions")
        if not isinstance(schema_versions, list) or not schema_versions or not all(
            isinstance(value, str) and value for value in schema_versions
        ):
            raise RegistryError(f"form {form_id}: schema_versions must preserve at least one version")
        output = raw_entry.get("public_output")
        if not isinstance(output, dict) or output.get("route") not in ALLOWED_PUBLIC_ROUTES:
            raise RegistryError(f"form {form_id}: invalid public_output route")
        documents = output.get("documents")
        if not isinstance(documents, list) or not all(isinstance(value, str) for value in documents):
            raise RegistryError(f"form {form_id}: public_output documents must be a list")
        route = output["route"]
        if privacy_class in never_publish and (route != "never" or documents):
            raise RegistryError(f"form {form_id}: privacy class can never publish")
        if route == "rule-gated-aggregate" and privacy_class not in publishable:
            raise RegistryError(f"form {form_id}: privacy class cannot use public output")
        if route == "rule-gated-aggregate" and not documents:
            raise RegistryError(f"form {form_id}: aggregate route requires named documents")
        unapproved = [value for value in documents if value not in public_documents]
        if unapproved:
            raise RegistryError(f"form {form_id}: {unapproved[0]} is not an approved public document")
        if route == "never" and documents:
            raise RegistryError(f"form {form_id}: never route cannot name documents")


def publication_allowed(entry: dict[str, Any], sink: str) -> bool:
    output = entry.get("public_output", {})
    return sink == "public_stats" and output.get("route") == "rule-gated-aggregate"


def render_landing_fixture(registry: dict[str, Any]) -> str:
    cards: list[str] = []
    for entry in registry["forms"]:
        if entry["trial_status"] != "approved-for-trial" or not entry["field_landing"]:
            continue
        cards.append(
            '    <article class="form-card" data-form-id="{id}" data-kind="{kind}">\n'
            '      <h2>{title}</h2>\n'
            '      <p>Output home: <code>{home}</code></p>\n'
            '      <a href="{path}">Open form</a>\n'
            "    </article>".format(
                id=html.escape(entry["id"], quote=True),
                kind=html.escape(entry["kind"], quote=True),
                title=html.escape(entry["title"]),
                home=html.escape(entry["reading_home"]),
                path=html.escape(entry["file_path"], quote=True),
            )
        )
    return """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Generated form landing fixture</title></head>
<body>
  <main data-registry-version="{version}">
{cards}
  </main>
</body>
</html>
""".format(version=html.escape(registry["registry_version"], quote=True), cards="\n".join(cards))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--render", type=Path)
    arguments = parser.parse_args()
    try:
        registry = load_registry(arguments.registry)
        validate_registry(registry, arguments.root.resolve())
        if arguments.render:
            arguments.render.parent.mkdir(parents=True, exist_ok=True)
            arguments.render.write_text(render_landing_fixture(registry), encoding="utf-8")
    except (OSError, RegistryError) as error:
        print(f"registry validation failed: {error}")
        return 1
    print(f"registry validation passed: {len(registry['forms'])} forms, {len(registry['homes'])} homes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
