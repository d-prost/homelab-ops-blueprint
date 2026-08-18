#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "scripts" / "validate-stack-contracts.py"
FIXTURE = REPO / "tests" / "fixtures" / "operational-coverage" / "stateful-demo"
EXPECTED_PROVENANCE = {
    "service",
    "stateful",
    "persistent_storage",
    "backup_policy",
    "restore_runbook",
    "restore_verification",
    "monitoring_required",
}


def load_validator():
    spec = importlib.util.spec_from_file_location("stack_contract_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load stack contract validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mutate_contract(stack_dir: Path, callback) -> None:
    path = stack_dir / "stack.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    callback(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def expect_contract_error(module, callback, message: str) -> None:
    with tempfile.TemporaryDirectory(prefix="blueprint-coverage-negative.") as raw_tmp:
        stack_dir = Path(raw_tmp) / "stateful-demo"
        shutil.copytree(FIXTURE, stack_dir)
        callback(stack_dir)
        try:
            module.validate_operational_coverage(stack_dir)
        except module.ContractError as exc:
            if message not in str(exc):
                raise AssertionError(f"unexpected validation error: {exc}") from exc
        else:
            raise AssertionError("invalid operational coverage contract was accepted")


def assert_provenance(report: dict) -> None:
    services = report.get("services")
    assert isinstance(services, list) and len(services) == 1
    provenance = services[0].get("provenance")
    assert isinstance(provenance, dict)
    assert set(provenance) == EXPECTED_PROVENANCE

    kinds: set[str] = set()
    for field, evidence in provenance.items():
        if field == "persistent_storage":
            assert isinstance(evidence, list) and evidence
            for record in evidence:
                assert isinstance(record.get("target"), str)
                entries = record.get("evidence")
                assert isinstance(entries, list) and entries
                kinds.update(entry["kind"] for entry in entries)
        else:
            assert isinstance(evidence, list) and evidence
            kinds.update(entry["kind"] for entry in evidence)
    assert kinds == {"deterministic", "explicit"}
    assert "confidence" not in json.dumps(report)


def assert_operations_opt_in(module) -> None:
    with tempfile.TemporaryDirectory(prefix="blueprint-coverage-routing.") as raw_tmp:
        test_root = Path(raw_tmp)
        stack_dir = test_root / "stacks" / "dozzle"
        shutil.copytree(REPO / "stacks" / "dozzle", stack_dir)
        mutate_contract(stack_dir, lambda data: data.update({"operations": {}}))

        calls: list[Path] = []
        original_root = module.ROOT
        original_validator = module.validate_operational_coverage
        module.ROOT = test_root
        module.validate_operational_coverage = lambda path: calls.append(path) or {
            "schema_version": 1,
            "services": [],
        }
        try:
            module.validate_stack(stack_dir)
        finally:
            module.ROOT = original_root
            module.validate_operational_coverage = original_validator

        assert calls == [stack_dir]


def main() -> int:
    module = load_validator()
    report = module.validate_operational_coverage(FIXTURE)
    assert report["schema_version"] == 1
    service = report["services"][0]
    assert service["service"] == "demo"
    assert service["stateful"] is True
    assert service["persistent_storage"] == ["/var/lib/example"]
    assert service["backup_policy"] == "critical"
    assert service["restore_runbook"] == "recovery/example.md"
    assert service["restore_verification"] == "functional"
    assert service["monitoring_required"] is True
    assert_provenance(report)
    assert_operations_opt_in(module)

    expect_contract_error(
        module,
        lambda stack: mutate_contract(
            stack,
            lambda data: data["operations"]["services"].update(
                {"missing": data["operations"]["services"].pop("demo")}
            ),
        ),
        "references unknown Compose service",
    )
    expect_contract_error(
        module,
        lambda stack: mutate_contract(
            stack,
            lambda data: data["operations"]["services"]["demo"]["persistent_mounts"][0].update(
                {"target": "/var/lib/missing"}
            ),
        ),
        "is not present in canonical Compose mounts",
    )
    expect_contract_error(
        module,
        lambda stack: mutate_contract(
            stack,
            lambda data: data["operations"]["services"]["demo"].pop("backup"),
        ),
        "backup must be a mapping",
    )
    expect_contract_error(
        module,
        lambda stack: mutate_contract(
            stack,
            lambda data: data["operations"]["services"]["demo"]["restore"].pop("runbook"),
        ),
        "restore runbook is not a safe relative file",
    )
    expect_contract_error(
        module,
        lambda stack: mutate_contract(
            stack,
            lambda data: data["operations"]["services"]["demo"]["restore"].pop("verification"),
        ),
        "restore verification must be a non-empty identifier",
    )
    expect_contract_error(
        module,
        lambda stack: mutate_contract(
            stack,
            lambda data: data["operations"]["services"]["demo"].pop("monitoring"),
        ),
        "monitoring must be a mapping",
    )

    print(
        "Operational coverage tests passed: opt-in routing, 1 stateful service, "
        "7/7 provenance fields, 6 rejection cases."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
