#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import yaml

SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReadinessError(RuntimeError):
    pass


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ReadinessError(f"{path}: expected a mapping")
    return data


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReadinessError(f"{path}: invalid JSON") from exc
    if not isinstance(data, dict):
        raise ReadinessError(f"{path}: expected a JSON object")
    return data


def require_mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ReadinessError(f"{label} must be an object")
    return value


def require_exact_keys(mapping: dict, required: set[str], label: str) -> None:
    keys = set(mapping)
    missing = sorted(required - keys)
    unknown = sorted(keys - required)
    if missing:
        raise ReadinessError(f"{label} is missing required field(s): {', '.join(missing)}")
    if unknown:
        raise ReadinessError(f"{label} contains unsupported field(s): {', '.join(unknown)}")


def require_true_fields(mapping: dict, keys: tuple[str, ...], label: str) -> None:
    for key in keys:
        if mapping.get(key) is not True:
            raise ReadinessError(f"{label}.{key} must be true")


def safe_relative_file(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value.endswith("/"):
        raise ReadinessError(f"{label} must be a safe relative file")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ReadinessError(f"{label} must be a safe relative file")
    return value


def file_sha256(path: Path, label: str) -> str:
    if not path.is_file():
        raise ReadinessError(f"{label} does not exist: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stateful_services(stack: dict) -> dict[str, dict]:
    operations = stack.get("operations")
    if operations is None:
        return {}
    operations = require_mapping(operations, "operations")
    services = require_mapping(operations.get("services"), "operations.services")

    selected: dict[str, dict] = {}
    for name, raw in sorted(services.items()):
        if not isinstance(name, str) or not name:
            raise ReadinessError("operations.services contains an invalid service name")
        service = require_mapping(raw, f"operations.services.{name}")
        if service.get("stateful") is not True:
            continue
        selected[name] = {
            "persistent_mounts": service.get("persistent_mounts"),
            "backup": service.get("backup"),
            "restore": service.get("restore"),
        }
    return selected


def recovery_proof_contract(stack_path: Path) -> dict:
    stack = load_yaml(stack_path)
    stack_name = stack_path.parent.name
    services = stateful_services(stack)
    if not services:
        return {"schema_version": 1, "stack": stack_name, "services": {}}

    stack_dir = stack_path.parent
    managed_files = stack.get("stack_managed_files")
    if not isinstance(managed_files, list) or not managed_files:
        raise ReadinessError("stateful stack requires non-empty stack_managed_files")

    managed_contract: list[dict] = []
    managed_payload_sha256: dict[str, str] = {}
    for index, raw in enumerate(managed_files, 1):
        record = require_mapping(raw, f"stack_managed_files[{index}]")
        src = safe_relative_file(record.get("src"), f"stack_managed_files[{index}].src")
        managed_contract.append(record)
        managed_payload_sha256[src] = file_sha256(
            stack_dir / src, f"managed payload {src}"
        )

    restore_runbook_sha256: dict[str, str] = {}
    for service_name, service in services.items():
        restore = require_mapping(service.get("restore"), f"{service_name}.restore")
        runbook = safe_relative_file(
            restore.get("runbook"), f"{service_name}.restore.runbook"
        )
        restore_runbook_sha256[runbook] = file_sha256(
            stack_dir / runbook, f"restore runbook {runbook}"
        )

    return {
        "schema_version": 1,
        "stack": stack_name,
        "services": services,
        "runtime_contract": {
            "stack_compose_dest": stack.get("stack_compose_dest"),
            "stack_expected_services": stack.get("stack_expected_services"),
            "stack_functional_checks": stack.get("stack_functional_checks"),
            "stack_managed_files": managed_contract,
            "managed_payload_sha256": managed_payload_sha256,
        },
        "restore_runbook_sha256": restore_runbook_sha256,
    }


def contract_hash(contract: dict) -> str:
    canonical = json.dumps(
        contract, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReadinessError(f"{label} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReadinessError(f"{label} is not a valid RFC3339 timestamp") from exc
    return parsed.astimezone(timezone.utc)


def secure_evidence_path(path: Path, forbidden_root: Path | None = None) -> Path:
    if path.is_symlink():
        raise ReadinessError("recovery evidence must not be a symlink")
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ReadinessError(f"recovery evidence does not exist: {path}") from exc
    if not resolved.is_file():
        raise ReadinessError("recovery evidence must be a regular file")

    if forbidden_root is not None:
        root = forbidden_root.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            pass
        else:
            raise ReadinessError(
                "recovery evidence must live outside the public repository tree"
            )

    if resolved.stat().st_mode & 0o022:
        raise ReadinessError("recovery evidence must not be group- or world-writable")
    return resolved


def validate_service_coverage(value: object, expected: list[str]) -> None:
    if not isinstance(value, list) or not value:
        raise ReadinessError("covered_services must be a non-empty list")
    if any(not isinstance(item, str) or not item for item in value):
        raise ReadinessError("covered_services contains an invalid service name")
    if len(value) != len(set(value)):
        raise ReadinessError("covered_services contains duplicates")
    if sorted(value) != expected:
        raise ReadinessError(
            "recovery evidence does not cover the exact stateful service set"
        )


def validate_evidence(
    stack_path: Path,
    evidence_path: Path | None,
    max_backup_age_seconds: int | None,
    now: datetime,
    *,
    current_contract_path: Path | None = None,
    forbidden_evidence_root: Path | None = None,
) -> dict:
    contract = recovery_proof_contract(stack_path)
    stack_name = contract["stack"]
    services = sorted(contract["services"])
    digest = contract_hash(contract)

    current_services: list[str] = []
    if current_contract_path is not None and current_contract_path.is_file():
        current_services = sorted(stateful_services(load_yaml(current_contract_path)))

    if not services:
        if current_services:
            raise ReadinessError(
                "current control plane declares this stack stateful, but the selected payload lacks a stateful recovery contract"
            )
        return {
            "schema_version": 1,
            "stack": stack_name,
            "stateful": False,
            "ready": True,
            "contract_hash": digest,
            "reason": "no stateful services declared",
        }

    if evidence_path is None:
        raise ReadinessError("stateful stack requires --evidence")
    if max_backup_age_seconds is None or max_backup_age_seconds <= 0:
        raise ReadinessError(
            "stateful stack requires a positive --max-backup-age-seconds environment policy"
        )

    evidence = load_json(
        secure_evidence_path(evidence_path, forbidden_evidence_root)
    )
    require_exact_keys(
        evidence,
        {
            "schema_version",
            "contract_hash",
            "covered_services",
            "disposition",
            "isolated_restore",
            "recovery_objectives",
            "rollback_compatibility",
            "backup_receipt",
        },
        "recovery evidence",
    )
    if evidence.get("schema_version") != 1:
        raise ReadinessError("unsupported evidence schema_version")
    evidence_hash = evidence.get("contract_hash")
    if not isinstance(evidence_hash, str) or not SHA256.fullmatch(evidence_hash):
        raise ReadinessError("contract_hash must be a lowercase SHA-256 digest")
    if evidence_hash != digest:
        raise ReadinessError(
            "recovery evidence does not match the current public stack generation"
        )
    validate_service_coverage(evidence.get("covered_services"), services)
    if evidence.get("disposition") != "ready":
        raise ReadinessError("recovery evidence disposition is not ready")

    restore = require_mapping(evidence.get("isolated_restore"), "isolated_restore")
    require_exact_keys(
        restore,
        {"passed", "functional_verification", "production_unchanged"},
        "isolated_restore",
    )
    require_true_fields(
        restore,
        ("passed", "functional_verification", "production_unchanged"),
        "isolated_restore",
    )

    objectives = require_mapping(
        evidence.get("recovery_objectives"), "recovery_objectives"
    )
    require_exact_keys(objectives, {"rpo_met", "rto_met"}, "recovery_objectives")
    require_true_fields(objectives, ("rpo_met", "rto_met"), "recovery_objectives")

    rollback = require_mapping(
        evidence.get("rollback_compatibility"), "rollback_compatibility"
    )
    require_exact_keys(
        rollback,
        {"configuration_rollback_safe"},
        "rollback_compatibility",
    )
    require_true_fields(
        rollback,
        ("configuration_rollback_safe",),
        "rollback_compatibility",
    )

    backup = require_mapping(evidence.get("backup_receipt"), "backup_receipt")
    require_exact_keys(backup, {"observed_at"}, "backup_receipt")
    observed_at = parse_utc(
        backup.get("observed_at"), "backup_receipt.observed_at"
    )
    age = (now.astimezone(timezone.utc) - observed_at).total_seconds()
    if age < 0:
        raise ReadinessError("backup_receipt.observed_at is in the future")
    if age > max_backup_age_seconds:
        raise ReadinessError(
            f"backup evidence is stale: age={int(age)}s max={max_backup_age_seconds}s"
        )

    return {
        "schema_version": 1,
        "stack": stack_name,
        "stateful": True,
        "ready": True,
        "contract_hash": digest,
        "services": services,
        "backup_age_seconds": int(age),
        "max_backup_age_seconds": max_backup_age_seconds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate private recovery-readiness evidence against an exact public stack generation."
        )
    )
    parser.add_argument("stack", type=Path, help="Path to selected stack.yml")
    parser.add_argument(
        "--current-contract",
        type=Path,
        help="Current control-plane stack.yml used to prevent historical stateful-classification bypass",
    )
    parser.add_argument("--evidence", type=Path, help="Private recovery evidence JSON")
    parser.add_argument(
        "--max-backup-age-seconds",
        type=int,
        help="Environment policy for acceptable backup evidence age",
    )
    parser.add_argument(
        "--forbid-evidence-under",
        type=Path,
        help="Reject evidence stored under this public repository root",
    )
    parser.add_argument("--now", help="Testing override: RFC3339 UTC timestamp")
    parser.add_argument("--print-contract-hash", action="store_true")
    args = parser.parse_args()

    contract = recovery_proof_contract(args.stack)
    digest = contract_hash(contract)
    if args.print_contract_hash:
        print(digest)
        return 0

    now = parse_utc(args.now, "--now") if args.now else datetime.now(timezone.utc)
    result = validate_evidence(
        args.stack,
        args.evidence,
        args.max_backup_age_seconds,
        now,
        current_contract_path=args.current_contract,
        forbidden_evidence_root=args.forbid_evidence_under,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ReadinessError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
