#!/usr/bin/env python3
"""Validate the public advisory-rule registry."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "advisory" / "rules.yml"

TOP_LEVEL_FIELDS = {"schema_version", "rules"}
RULE_FIELDS = {
    "id",
    "title",
    "category",
    "status",
    "source",
    "applies_when",
    "principle",
    "recommendation",
    "proof",
}
CATEGORIES = {
    "automation-safety",
    "ownership",
    "state-management",
    "transaction-safety",
}
RULE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ValidationError(ValueError):
    pass


def require_nonempty_string(value: object, field: str, rule_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{rule_id}: {field} must be a non-empty string")
    return value.strip()


def require_string_list(value: object, field: str, rule_id: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{rule_id}: {field} must be a non-empty list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                f"{rule_id}: {field} entries must be non-empty strings"
            )
        result.append(item.strip())
    return result


def validate_registry(path: Path = REGISTRY) -> list[dict[str, object]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValidationError("advisory registry must be a mapping")

    unknown_top = set(document) - TOP_LEVEL_FIELDS
    missing_top = TOP_LEVEL_FIELDS - set(document)
    if unknown_top or missing_top:
        raise ValidationError(
            f"advisory registry fields mismatch: "
            f"missing={sorted(missing_top)} unknown={sorted(unknown_top)}"
        )

    if document["schema_version"] != 1:
        raise ValidationError("advisory registry schema_version must be 1")

    rules = document["rules"]
    if not isinstance(rules, list) or not rules:
        raise ValidationError("advisory registry must contain at least one rule")

    seen: set[str] = set()
    validated: list[dict[str, object]] = []

    for index, raw_rule in enumerate(rules):
        if not isinstance(raw_rule, dict):
            raise ValidationError(f"rule {index} must be a mapping")

        rule_id = raw_rule.get("id")
        if not isinstance(rule_id, str) or not RULE_ID.fullmatch(rule_id):
            raise ValidationError(f"rule {index}: invalid rule id")

        unknown = set(raw_rule) - RULE_FIELDS
        missing = RULE_FIELDS - set(raw_rule)
        if unknown or missing:
            raise ValidationError(
                f"{rule_id}: rule fields mismatch: "
                f"missing={sorted(missing)} unknown={sorted(unknown)}"
            )

        if rule_id in seen:
            raise ValidationError(f"duplicate advisory rule id: {rule_id}")
        seen.add(rule_id)

        require_nonempty_string(raw_rule["title"], "title", rule_id)
        require_nonempty_string(raw_rule["principle"], "principle", rule_id)
        require_nonempty_string(
            raw_rule["recommendation"], "recommendation", rule_id
        )
        require_string_list(raw_rule["applies_when"], "applies_when", rule_id)
        require_string_list(raw_rule["proof"], "proof", rule_id)

        if raw_rule["category"] not in CATEGORIES:
            raise ValidationError(
                f"{rule_id}: unsupported category {raw_rule['category']!r}"
            )
        if raw_rule["status"] != "advisory":
            raise ValidationError(
                f"{rule_id}: status must remain 'advisory'; "
                "enforcement requires a separate mechanism"
            )
        if raw_rule["source"] != "production-derived":
            raise ValidationError(
                f"{rule_id}: source must be the public-safe "
                "'production-derived' classification"
            )

        validated.append(raw_rule)

    return validated


def main() -> int:
    rules = validate_registry()
    print(f"Advisory registry validation passed: {len(rules)} rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
