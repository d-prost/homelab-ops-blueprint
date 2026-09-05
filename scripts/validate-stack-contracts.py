#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
STACKS = ROOT / "stacks"
SAFE_STACK = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SAFE_SERVICE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SAFE_FILE = re.compile(r"^[A-Za-z0-9._/-]+$")
SAFE_MODE = re.compile(r"^0[0-7]{3}$")
IMAGE = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
TARGET = re.compile(r"^/(opt|srv)/homelab-ops/[A-Za-z0-9._/-]+$")
CONTRACT_FIELDS = {
    "stack_target_dir",
    "stack_compose_dest",
    "stack_expected_services",
    "stack_managed_files",
    "stack_functional_checks",
    "operations",
}


class ContractError(RuntimeError):
    pass


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def require_mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a mapping")
    return value


def require_list(value: object, label: str) -> list:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{label} must be a non-empty list")
    return value


def safe_relative_file(value: object, label: str) -> str:
    if not isinstance(value, str) or not SAFE_FILE.fullmatch(value):
        raise ContractError(f"{label} is not a safe relative file")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or "//" in value
        or value.endswith("/")
    ):
        raise ContractError(f"{label} is not a safe relative file")
    return value


def safe_target(value: object, label: str) -> str:
    if not isinstance(value, str) or not TARGET.fullmatch(value):
        raise ContractError(f"{label} is outside the allowed target roots")
    path = PurePosixPath(value)
    if ".." in path.parts or "." in path.parts or "//" in value:
        raise ContractError(f"{label} contains an unsafe path component")
    return value.rstrip("/")


def load_manifest(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        raise ContractError(f"missing manifest: {display_path(path)}")
    records: list[tuple[str, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw or raw.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 2:
            raise ContractError(f"{display_path(path)}:{line_number}: expected two TSV fields")
        source = safe_relative_file(fields[0], f"manifest source line {line_number}")
        destination = fields[1]
        if not destination.startswith("/"):
            raise ContractError(f"manifest destination line {line_number} must be absolute")
        records.append((source, destination))
    if not records or len(records) != len(set(records)):
        raise ContractError(f"{display_path(path)} is empty or contains duplicate rows")
    return records


def validate_stack(stack_dir: Path) -> None:
    stack = stack_dir.name
    if not SAFE_STACK.fullmatch(stack):
        raise ContractError(f"unsafe stack name: {stack}")

    contract = require_mapping(load(stack_dir / "stack.yml"), f"{stack}:stack.yml")
    unknown_fields = sorted(set(contract) - CONTRACT_FIELDS)
    if unknown_fields:
        raise ContractError(
            f"{stack}: unknown stack.yml field(s): {', '.join(unknown_fields)}"
        )

    compose = require_mapping(load(stack_dir / "compose.yaml"), f"{stack}:compose.yaml")
    target_dir = safe_target(contract.get("stack_target_dir"), f"{stack}:stack_target_dir")
    compose_dest = safe_relative_file(
        contract.get("stack_compose_dest"), f"{stack}:stack_compose_dest"
    )

    services = require_mapping(compose.get("services"), f"{stack}:compose services")
    expected = require_list(contract.get("stack_expected_services"), f"{stack}:expected services")
    if any(not isinstance(service, str) or not SAFE_SERVICE.fullmatch(service) for service in expected):
        raise ContractError(f"{stack}: unsafe expected service")
    if set(services) != set(expected):
        raise ContractError(f"{stack}: service contract mismatch")

    checks = require_list(contract.get("stack_functional_checks"), f"{stack}:functional checks")
    check_names: set[str] = set()
    for index, raw_check in enumerate(checks, 1):
        check = require_mapping(raw_check, f"{stack}:functional check #{index}")
        name = check.get("name")
        if not isinstance(name, str) or not SAFE_SERVICE.fullmatch(name) or name in check_names:
            raise ContractError(f"{stack}: invalid or duplicate functional check name")
        if check.get("service") not in expected:
            raise ContractError(f"{stack}: functional check references an unknown service")
        statuses = check.get("status_codes")
        if not isinstance(statuses, list) or not statuses or any(
            not isinstance(code, int) or isinstance(code, bool) or code < 100 or code > 599
            for code in statuses
        ):
            raise ContractError(f"{stack}: functional check has invalid status codes")
        check_names.add(name)

    managed_files = require_list(contract.get("stack_managed_files"), f"{stack}:managed files")
    expected_manifest: list[tuple[str, str]] = []
    destinations: set[str] = set()
    for index, raw_file in enumerate(managed_files, 1):
        file_record = require_mapping(raw_file, f"{stack}:managed file #{index}")
        source = safe_relative_file(file_record.get("src"), f"{stack}:managed src")
        destination = safe_relative_file(file_record.get("dest"), f"{stack}:managed dest")
        mode = file_record.get("mode")
        if not isinstance(mode, str) or not SAFE_MODE.fullmatch(mode):
            raise ContractError(f"{stack}: managed file has an invalid mode")
        if destination in destinations:
            raise ContractError(f"{stack}: duplicate managed destination: {destination}")
        if not (stack_dir / source).is_file():
            raise ContractError(f"{stack}: managed source is missing: {source}")
        destinations.add(destination)
        expected_manifest.append((source, f"{target_dir}/{destination}"))

    if ("compose.yaml", f"{target_dir}/{compose_dest}") not in expected_manifest:
        raise ContractError(f"{stack}: compose.yaml is not mapped to stack_compose_dest")
    if ("defaults.env", f"{target_dir}/defaults.env") not in expected_manifest:
        raise ContractError(f"{stack}: defaults.env is not managed")
    if load_manifest(stack_dir / "MANIFEST.tsv") != expected_manifest:
        raise ContractError(f"{stack}: MANIFEST.tsv differs from stack.yml")

    images = [
        line.split("=", 1)[1]
        for line in (stack_dir / "defaults.env").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "_IMAGE=" in line
    ]
    if not images or any(not IMAGE.fullmatch(image) for image in images):
        raise ContractError(f"{stack}: images must be pinned by digest")

    if "operations" in contract:
        validate_operational_coverage(stack_dir)


def compose_canonical_model(stack_dir: Path) -> dict:
    compose_path = stack_dir / "compose.yaml"
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "config", "--format", "json"],
            cwd=stack_dir,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise ContractError("docker compose is required for operational coverage") from exc
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise ContractError(f"docker compose config failed: {detail}")
    try:
        return require_mapping(json.loads(result.stdout), "Compose canonical model")
    except json.JSONDecodeError as exc:
        raise ContractError("docker compose config returned invalid JSON") from exc


def _coverage_evidence(locator: str, compose_locator: str | None = None) -> list[dict[str, str]]:
    evidence = [{"kind": "explicit", "source": "stack.yml", "locator": locator}]
    if compose_locator:
        evidence.append(
            {"kind": "deterministic", "source": "docker compose canonical model", "locator": compose_locator}
        )
    return evidence


def _required_identifier(mapping: dict, key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not SAFE_SERVICE.fullmatch(value):
        raise ContractError(f"{label} must be a non-empty identifier")
    return value


def validate_operational_coverage(stack_dir: Path) -> dict:
    stack = stack_dir.name
    contract = require_mapping(load(stack_dir / "stack.yml"), f"{stack}:stack.yml")
    operations = require_mapping(contract.get("operations"), f"{stack}:operations")
    declared = require_mapping(operations.get("services"), f"{stack}:operations services")
    canonical = compose_canonical_model(stack_dir)
    compose_services = require_mapping(canonical.get("services"), f"{stack}:canonical services")
    covered: list[dict] = []

    for service_name, raw_ops in sorted(declared.items()):
        if not isinstance(service_name, str) or not SAFE_SERVICE.fullmatch(service_name):
            raise ContractError(f"{stack}:operations contains an unsafe service name")
        if service_name not in compose_services:
            raise ContractError(f"{stack}:{service_name}: operational coverage references unknown Compose service")

        service_ops = require_mapping(raw_ops, f"{stack}:{service_name}:operations")
        stateful = service_ops.get("stateful")
        if not isinstance(stateful, bool):
            raise ContractError(f"{stack}:{service_name}: stateful must be boolean")
        if not stateful:
            continue

        canonical_service = require_mapping(
            compose_services[service_name], f"{stack}:{service_name}:canonical service"
        )
        volumes = canonical_service.get("volumes") or []
        if not isinstance(volumes, list):
            raise ContractError(f"{stack}:{service_name}: canonical volumes must be a list")
        canonical_mounts = {
            volume.get("target") for volume in volumes if isinstance(volume, dict)
        }

        mounts = require_list(
            service_ops.get("persistent_mounts"), f"{stack}:{service_name}:persistent mounts"
        )
        persistent_storage: list[str] = []
        for index, raw_mount in enumerate(mounts):
            mount = require_mapping(raw_mount, f"{stack}:{service_name}:persistent mount #{index + 1}")
            target = mount.get("target")
            if not isinstance(target, str) or not target.startswith("/"):
                raise ContractError(f"{stack}:{service_name}: persistent mount target must be absolute")
            if target in persistent_storage:
                raise ContractError(f"{stack}:{service_name}: duplicate persistent mount target: {target}")
            if target not in canonical_mounts:
                raise ContractError(
                    f"{stack}:{service_name}: persistent mount {target} is not present in canonical Compose mounts"
                )
            persistent_storage.append(target)

        backup = require_mapping(service_ops.get("backup"), f"{stack}:{service_name}:backup")
        backup_policy = _required_identifier(backup, "policy", f"{stack}:{service_name}:backup policy")
        restore = require_mapping(service_ops.get("restore"), f"{stack}:{service_name}:restore")
        restore_runbook = safe_relative_file(
            restore.get("runbook"), f"{stack}:{service_name}:restore runbook"
        )
        if not (stack_dir / restore_runbook).is_file():
            raise ContractError(f"{stack}:{service_name}: restore runbook does not exist: {restore_runbook}")
        restore_verification = _required_identifier(
            restore, "verification", f"{stack}:{service_name}:restore verification"
        )
        monitoring = require_mapping(service_ops.get("monitoring"), f"{stack}:{service_name}:monitoring")
        monitoring_required = monitoring.get("required")
        if not isinstance(monitoring_required, bool):
            raise ContractError(f"{stack}:{service_name}: monitoring required must be boolean")

        base = f"operations.services.{service_name}"
        covered.append(
            {
                "service": service_name,
                "stateful": True,
                "persistent_storage": persistent_storage,
                "backup_policy": backup_policy,
                "restore_runbook": restore_runbook,
                "restore_verification": restore_verification,
                "monitoring_required": monitoring_required,
                "provenance": {
                    "service": _coverage_evidence(base, f"services.{service_name}"),
                    "stateful": _coverage_evidence(f"{base}.stateful"),
                    "persistent_storage": [
                        {
                            "target": target,
                            "evidence": _coverage_evidence(
                                f"{base}.persistent_mounts[{index}].target",
                                f"services.{service_name}.volumes[target={target}]",
                            ),
                        }
                        for index, target in enumerate(persistent_storage)
                    ],
                    "backup_policy": _coverage_evidence(f"{base}.backup.policy"),
                    "restore_runbook": _coverage_evidence(f"{base}.restore.runbook"),
                    "restore_verification": _coverage_evidence(f"{base}.restore.verification"),
                    "monitoring_required": _coverage_evidence(f"{base}.monitoring.required"),
                },
            }
        )

    if not covered:
        raise ContractError(f"{stack}: no stateful services declared for operational coverage")
    return {"schema_version": 1, "services": covered}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stack-dir",
        action="append",
        type=Path,
        default=[],
        help="validate only this stack directory; may be supplied more than once",
    )
    args = parser.parse_args()

    if args.stack_dir:
        managed = [path.resolve() for path in args.stack_dir]
    else:
        managed = sorted(path.parent for path in STACKS.glob("*/stack.yml"))

    if not managed:
        raise ContractError("no managed stack contracts found")
    for stack_dir in managed:
        validate_stack(stack_dir)
    print(f"Validated {len(managed)} managed stack contract(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
