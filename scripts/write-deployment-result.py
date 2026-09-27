#!/usr/bin/env python3
"""Write a durable, address-free terminal result separate from accepted state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

COMMIT = re.compile(r"[0-9a-f]{40}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
STACK = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9._:-]+\Z")
OUTCOMES = {
    "ACCEPTED": {"NOT_NEEDED"},
    "PRE_MUTATION_REFUSAL": {"NOT_NEEDED"},
    "ACCEPTANCE_PERSISTENCE_FAILED": {"NOT_ATTEMPTED"},
    "REJECTED_ROLLBACK_FAILED": {"UNAVAILABLE", "FAILED"},
    "REJECTED_ROLLBACK_VERIFIED": {"VERIFIED"},
}


class ResultError(RuntimeError):
    pass


def make_report(args: argparse.Namespace) -> dict:
    if not STACK.fullmatch(args.stack):
        raise ResultError("unsafe stack name")
    if not IDENTIFIER.fullmatch(args.transaction_id):
        raise ResultError("unsafe transaction ID")
    for name in ("candidate_commit", "tooling_commit"):
        if not COMMIT.fullmatch(getattr(args, name)):
            raise ResultError(f"invalid {name}")
    if args.previous_commit and not COMMIT.fullmatch(args.previous_commit):
        raise ResultError("invalid previous commit")
    for name in ("contract_hash", "manifest_hash"):
        if not HASH.fullmatch(getattr(args, name)):
            raise ResultError(f"invalid {name}")
    if args.previous_record_id and not HASH.fullmatch(args.previous_record_id):
        raise ResultError("invalid previous record ID")
    if not args.target_hostname or "|" in args.target_hostname or "|" in args.target_machine_id:
        raise ResultError("invalid declared target identity")
    if args.result not in OUTCOMES or args.rollback_result not in OUTCOMES[args.result]:
        raise ResultError("inconsistent terminal and rollback results")
    target_id = hashlib.sha256(
        f"{args.target_hostname}|{args.target_machine_id}".encode()
    ).hexdigest()
    return {
        "schema_version": 1,
        "stack": args.stack,
        "transaction_id": args.transaction_id,
        "candidate_commit": args.candidate_commit,
        "tooling_commit": args.tooling_commit,
        "previous_commit": args.previous_commit,
        "previous_record_id": args.previous_record_id,
        "stack_contract_id": f"sha256:{args.contract_hash}",
        "manifest_id": f"sha256:{args.manifest_hash}",
        "target_id": f"sha256:{target_id}",
        "result": args.result,
        "rollback_result": args.rollback_result,
    }


def atomic_write(destination: Path, report: dict) -> None:
    destination.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    payload = (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd, raw_temp = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    temporary = Path(raw_temp)
    try:
        os.fchmod(fd, 0o640)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--stack", required=True)
    parser.add_argument("--transaction-id", required=True)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--tooling-commit", required=True)
    parser.add_argument("--previous-commit", default="")
    parser.add_argument("--previous-record-id", default="")
    parser.add_argument("--contract-hash", required=True)
    parser.add_argument("--manifest-hash", required=True)
    parser.add_argument("--target-hostname", required=True)
    parser.add_argument("--target-machine-id", default="")
    parser.add_argument("--result", required=True)
    parser.add_argument("--rollback-result", required=True)
    args = parser.parse_args()
    atomic_write(args.destination, make_report(args))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ResultError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
