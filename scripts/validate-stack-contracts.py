#!/usr/bin/env python3
from __future__ import annotations

import re
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


class ContractError(RuntimeError):
    pass


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
    if path.is_absolute() or ".." in path.parts or "." in path.parts or value.endswith("/"):
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
        raise ContractError(f"missing manifest: {path.relative_to(ROOT)}")
    records: list[tuple[str, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw or raw.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 2:
            raise ContractError(f"{path.relative_to(ROOT)}:{line_number}: expected two TSV fields")
        source = safe_relative_file(fields[0], f"manifest source line {line_number}")
        destination = fields[1]
        if not destination.startswith("/"):
            raise ContractError(f"manifest destination line {line_number} must be absolute")
        records.append((source, destination))
    if not records or len(records) != len(set(records)):
        raise ContractError(f"{path.relative_to(ROOT)} is empty or contains duplicate rows")
    return records


def validate_stack(stack_dir: Path) -> None:
    stack = stack_dir.name
    if not SAFE_STACK.fullmatch(stack):
        raise ContractError(f"unsafe stack name: {stack}")

    contract = require_mapping(load(stack_dir / "stack.yml"), f"{stack}:stack.yml")
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
            not isinstance(code, int) or isinstance(code, bool) or code < 100 or code > 599 for code in statuses
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


def main() -> int:
    managed = sorted(path.parent for path in STACKS.glob("*/stack.yml"))
    if not managed:
        raise ContractError("no managed stack contracts found")
    for stack_dir in managed:
        validate_stack(stack_dir)
    print(f"Validated {len(managed)} managed stack contract(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
