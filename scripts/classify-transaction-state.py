#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

COMMIT = re.compile(r"^[0-9a-f]{40}$")
HASH = re.compile(r"^[0-9a-f]{64}$")
TX = re.compile(r"^[A-Za-z0-9._:-]+$")
PHASES = {
    "PREPARED",
    "MUTATING",
    "RESTORING",
    "ACCEPTANCE_PENDING",
    "ACCEPTANCE_PERSISTENCE_FAILED",
}


class StateError(RuntimeError):
    pass


def parse_kv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        if "=" not in line:
            raise StateError(f"invalid state line in {path}: {line!r}")
        key, value = line.split("=", 1)
        if not key or key in values:
            raise StateError(f"invalid or duplicate state key in {path}: {key!r}")
        values[key] = value
    return values


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", required=True)
    parser.add_argument("--marker", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    if not args.marker.exists():
        print("NONE||||||")
        return 0

    marker = parse_kv(args.marker)
    required = {
        "transaction_id",
        "stack",
        "candidate_commit",
        "previous_accepted_commit",
        "previous_record_id",
        "phase",
    }
    if not required.issubset(marker):
        raise StateError("unresolved marker is missing required transaction fields")
    if marker["stack"] != args.stack:
        raise StateError("unresolved marker belongs to a different stack")
    if not TX.fullmatch(marker["transaction_id"]):
        raise StateError("unresolved marker has an unsafe transaction_id")
    if not COMMIT.fullmatch(marker["candidate_commit"]):
        raise StateError("unresolved marker has an invalid candidate commit")
    if marker["previous_accepted_commit"] and not COMMIT.fullmatch(
        marker["previous_accepted_commit"]
    ):
        raise StateError("unresolved marker has an invalid previous commit")
    if marker["previous_record_id"] and not HASH.fullmatch(marker["previous_record_id"]):
        raise StateError("unresolved marker has an invalid previous record id")
    if marker["phase"] not in PHASES:
        raise StateError(f"unresolved marker has an unknown phase: {marker['phase']}")

    action = "MANUAL"
    record_hash = ""

    if marker["phase"] == "PREPARED":
        action = "CLEANUP"
    elif marker["phase"] in {"MUTATING", "RESTORING"}:
        if marker["previous_accepted_commit"] and marker["previous_record_id"]:
            action = "RESTORE"
    elif marker["phase"] == "ACCEPTANCE_PENDING":
        if args.record.is_file() and args.receipt.is_file():
            record = parse_kv(args.record)
            receipt = parse_kv(args.receipt)
            record_hash = file_hash(args.record)
            if (
                record.get("transaction_id") == marker["transaction_id"]
                and receipt.get("transaction_id") == marker["transaction_id"]
                and receipt.get("record_sha256") == record_hash
            ):
                action = "ACCEPTED_STALE"

    fields = [
        action,
        marker["transaction_id"],
        marker["candidate_commit"],
        marker["previous_accepted_commit"],
        marker["previous_record_id"],
        marker["phase"],
        record_hash,
    ]
    print("|".join(fields))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StateError as exc:
        raise SystemExit(f"ERROR: INTERRUPTED_UNRESOLVED: {exc}")
