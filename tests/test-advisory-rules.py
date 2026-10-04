#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-advisory-rules.py"
REGISTRY = ROOT / "advisory" / "rules.yml"


def load_validator():
    spec = importlib.util.spec_from_file_location("advisory_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load advisory validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_error(module, document: dict, message: str) -> None:
    with tempfile.TemporaryDirectory(prefix="blueprint-advisory-negative.") as raw:
        path = Path(raw) / "rules.yml"
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        try:
            module.validate_registry(path)
        except module.ValidationError as exc:
            if message not in str(exc):
                raise AssertionError(f"unexpected validation error: {exc}") from exc
        else:
            raise AssertionError("invalid advisory registry was accepted")


def main() -> int:
    module = load_validator()
    rules = module.validate_registry(REGISTRY)
    ids = {rule["id"] for rule in rules}

    assert ids == {
        "acceptance-failure-needs-cutback",
        "detach-unused-control-streams",
        "one-content-authority",
        "persist-retry-state-before-mutation",
    }
    assert all(rule["status"] == "advisory" for rule in rules)
    assert all(rule["source"] == "production-derived" for rule in rules)

    document = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))

    duplicate = copy.deepcopy(document)
    duplicate["rules"].append(copy.deepcopy(duplicate["rules"][0]))
    expect_error(module, duplicate, "duplicate advisory rule id")

    unknown = copy.deepcopy(document)
    unknown["rules"][0]["private_evidence"] = "not allowed"
    expect_error(module, unknown, "unknown=['private_evidence']")

    enforced = copy.deepcopy(document)
    enforced["rules"][0]["status"] = "enforced"
    expect_error(module, enforced, "status must remain 'advisory'")

    empty_proof = copy.deepcopy(document)
    empty_proof["rules"][0]["proof"] = []
    expect_error(module, empty_proof, "proof must be a non-empty list")

    detailed_source = copy.deepcopy(document)
    detailed_source["rules"][0]["source"] = "private-pr-123"
    expect_error(module, detailed_source, "source must be the public-safe")

    print(
        "Advisory rule tests passed: 4 public-safe rules and 5 rejection cases."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
