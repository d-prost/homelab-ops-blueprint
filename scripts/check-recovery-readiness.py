#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml


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


def stateful_recovery_contract(stack: dict) -> dict:
    operations = stack.get("operations")
    if operations is None:
        return {"services": {}}
    if not isinstance(operations, dict):
        raise ReadinessError("operations must be a mapping")
    services = operations.get("services")
    if not isinstance(services, dict):
        raise ReadinessError("operations.services must be a mapping")

    selected: dict[str, dict] = {}
    for name, raw in sorted(services.items()):
        if not isinstance(raw, dict):
            raise ReadinessError(f"operations.services.{name} must be a mapping")
        if raw.get("stateful") is not True:
            continue
        selected[name] = {
            "persistent_mounts": raw.get("persistent_mounts"),
            "backup": raw.get("backup"),
            "restore": raw.get("restore"),
        }
    return {"services": selected}


def contract_hash(contract: dict) -> str:
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReadinessError(f"{label} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReadinessError(f"{label} is not a valid RFC3339 timestamp") from exc
    return parsed.astimezone(timezone.utc)


def require_pass(record: dict, key: str) -> None:
    value = record.get(key)
    if value is not True:
        raise ReadinessError(f"{key} must be true")


def validate_evidence(stack_path: Path, evidence_path: Path, max_backup_age_seconds: int, now: datetime) -> dict:
    stack = load_yaml(stack_path)
    contract = stateful_recovery_contract(stack)
    services = contract["services"]
    digest = contract_hash(contract)

    if not services:
        return {
            "schema_version": 1,
            "stateful": False,
            "ready": True,
            "contract_hash": digest,
            "reason": "no stateful services declared",
        }

    evidence = load_json(evidence_path)
    if evidence.get("schema_version") != 1:
        raise ReadinessError("unsupported evidence schema_version")
    if evidence.get("contract_hash") != digest:
        raise ReadinessError("recovery evidence does not match the current recovery contract")
    if evidence.get("disposition") != "ready":
        raise ReadinessError("recovery evidence disposition is not ready")

    restore = evidence.get("isolated_restore")
    if not isinstance(restore, dict):
        raise ReadinessError("isolated_restore must be an object")
    require_pass(restore, "passed")
    if restore.get("functional_verification") is not True:
        raise ReadinessError("isolated_restore.functional_verification must be true")

    backup = evidence.get("backup_receipt")
    if not isinstance(backup, dict):
        raise ReadinessError("backup_receipt must be an object")
    observed_at = parse_utc(backup.get("observed_at"), "backup_receipt.observed_at")
    age = (now.astimezone(timezone.utc) - observed_at).total_seconds()
    if age < 0:
        raise ReadinessError("backup_receipt.observed_at is in the future")
    if age > max_backup_age_seconds:
        raise ReadinessError(
            f"backup evidence is stale: age={int(age)}s max={max_backup_age_seconds}s"
        )

    return {
        "schema_version": 1,
        "stateful": True,
        "ready": True,
        "contract_hash": digest,
        "services": sorted(services),
        "backup_age_seconds": int(age),
        "max_backup_age_seconds": max_backup_age_seconds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate private recovery-readiness evidence against a public stack contract.")
    parser.add_argument("stack", type=Path, help="Path to stack.yml")
    parser.add_argument("--evidence", type=Path, help="Private recovery evidence JSON")
    parser.add_argument("--max-backup-age-seconds", type=int, help="Environment policy for acceptable backup evidence age")
    parser.add_argument("--now", help="Testing override: RFC3339 UTC timestamp")
    parser.add_argument("--print-contract-hash", action="store_true")
    args = parser.parse_args()

    stack = load_yaml(args.stack)
    contract = stateful_recovery_contract(stack)
    digest = contract_hash(contract)
    if args.print_contract_hash:
        print(digest)
        return 0
    if not contract["services"]:
        print(json.dumps({"schema_version": 1, "stateful": False, "ready": True, "contract_hash": digest}, sort_keys=True))
        return 0
    if args.evidence is None:
        raise ReadinessError("stateful stack requires --evidence")
    if args.max_backup_age_seconds is None or args.max_backup_age_seconds <= 0:
        raise ReadinessError("stateful stack requires a positive --max-backup-age-seconds environment policy")

    now = parse_utc(args.now, "--now") if args.now else datetime.now(timezone.utc)
    result = validate_evidence(args.stack, args.evidence, args.max_backup_age_seconds, now)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReadinessError as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
