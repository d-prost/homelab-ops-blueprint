#!/usr/bin/env python3
"""Compare a target's accepted record with local Git objects, without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

COMMIT = re.compile(r"[0-9a-f]{40}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
STACK = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*\Z")
OUTCOMES = {
    "ACCEPTED": {"NOT_NEEDED"},
    "PRE_MUTATION_REFUSAL": {"NOT_NEEDED"},
    "ACCEPTANCE_PERSISTENCE_FAILED": {"NOT_ATTEMPTED"},
    "REJECTED_ROLLBACK_FAILED": {"UNAVAILABLE", "FAILED"},
    "REJECTED_ROLLBACK_VERIFIED": {"VERIFIED"},
}


class RecordError(RuntimeError):
    pass


def parse_kv(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        raise RecordError(f"record is not a regular file: {path}")
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or "=" not in line:
            raise RecordError("record contains an invalid line")
        key, value = line.split("=", 1)
        if not key or key in values:
            raise RecordError("record contains an invalid or duplicate key")
        values[key] = value
    return values


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False
    )


def git_blob(repo: Path, commit: str, path: str) -> bytes | None:
    result = git(repo, "show", f"{commit}:{path}")
    return result.stdout if result.returncode == 0 else None


def valid_hash(value: str | None) -> bool:
    return isinstance(value, str) and bool(HASH.fullmatch(value))


def result_checks(repo: Path, history_ref: str, commit: str, tooling: str) -> dict[str, bool | None]:
    checks: dict[str, bool | None] = {}
    checks["candidate_commit_available"] = git(repo, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0
    checks["tooling_commit_available"] = git(repo, "cat-file", "-e", f"{tooling}^{{commit}}").returncode == 0
    history = git(repo, "rev-parse", "--verify", "--quiet", f"{history_ref}^{{commit}}")
    checks["history_ref_available"] = history.returncode == 0
    for label, selected in (("candidate", commit), ("tooling", tooling)):
        if checks["history_ref_available"] and checks[f"{label}_commit_available"]:
            checks[f"{label}_in_history"] = git(repo, "merge-base", "--is-ancestor", selected, history_ref).returncode == 0
        else:
            checks[f"{label}_in_history"] = None
    return checks


def disposition(checks: dict[str, bool | None]) -> tuple[str, list[str], list[str]]:
    unavailable = {"candidate_commit_available", "tooling_commit_available", "history_ref_available"}
    failures = sorted(name for name, value in checks.items() if value is False and name not in unavailable)
    unknown = sorted(name for name, value in checks.items() if value is None or (value is False and name in unavailable))
    status = "MISMATCH" if failures else "UNVERIFIABLE" if unknown else "MATCH"
    return status, failures, unknown


def compare(record_path: Path, repo: Path, history_ref: str, receipt_path: Path | None) -> dict:
    if not REF.fullmatch(history_ref) or ".." in history_ref or "//" in history_ref:
        raise RecordError("unsafe Git history ref")
    record = parse_kv(record_path)
    version = record.get("schema_version", "1")
    if version not in {"1", "2"}:
        raise RecordError("unsupported record schema_version")
    stack = record.get("stack", "")
    commit = record.get("commit", "")
    tooling = record.get("tooling_commit", "")
    if not STACK.fullmatch(stack) or not COMMIT.fullmatch(commit) or not COMMIT.fullmatch(tooling):
        raise RecordError("record contains an invalid stack or commit identity")
    if not valid_hash(record.get("contract_hash")) or not valid_hash(record.get("manifest_hash")):
        raise RecordError("record contains an invalid contract or manifest hash")

    checks = result_checks(repo, history_ref, commit, tooling)

    contract = git_blob(repo, commit, f"stacks/{stack}/stack.yml") if checks["candidate_commit_available"] else None
    manifest = git_blob(repo, commit, f"stacks/{stack}/MANIFEST.tsv") if checks["candidate_commit_available"] else None
    checks["contract_matches_git"] = None if not checks["candidate_commit_available"] else (
        contract is not None and hashlib.sha256(contract).hexdigest() == record["contract_hash"]
    )
    checks["manifest_matches_git"] = None if not checks["candidate_commit_available"] else (
        manifest is not None and hashlib.sha256(manifest).hexdigest() == record["manifest_hash"]
    )

    if version == "2":
        hostname = record.get("target_hostname", "")
        machine_id = record.get("target_machine_id", "")
        if not hostname or "|" in hostname or "|" in machine_id:
            raise RecordError("record contains an invalid target identity")
        target_hash = hashlib.sha256(f"{hostname}|{machine_id}".encode()).hexdigest()
        checks["stack_contract_id_matches"] = record.get("stack_contract_id") == f"sha256:{record['contract_hash']}"
        checks["manifest_id_matches"] = record.get("manifest_id") == f"sha256:{record['manifest_hash']}"
        checks["target_id_matches"] = record.get("target_id") == f"sha256:{target_hash}"
        verification_id = record.get("verification_result_id", "")
        checks["verification_result_declared"] = (
            record.get("verified") == "functional"
            and record.get("verification_result") == "PASS"
            and verification_id.startswith("sha256:")
            and valid_hash(verification_id[7:])
        )
    else:
        checks["legacy_record"] = True

    if receipt_path is not None:
        receipt = parse_kv(receipt_path)
        checks["receipt_matches"] = (
            receipt.get("transaction_id") == record.get("transaction_id")
            and receipt.get("record_sha256") == hashlib.sha256(record_path.read_bytes()).hexdigest()
        )

    status, failures, unknown = disposition(checks)
    return {
        "schema_version": 1,
        "record_schema_version": int(version),
        "stack": stack,
        "candidate_commit": commit,
        "history_ref": history_ref,
        "status": status,
        "checks": checks,
        "failures": failures,
        "unknown": unknown,
    }


def compare_result(path: Path, repo: Path, history_ref: str) -> dict:
    if not REF.fullmatch(history_ref) or ".." in history_ref or "//" in history_ref:
        raise RecordError("unsafe Git history ref")
    if not path.is_file() or path.is_symlink():
        raise RecordError(f"result is not a regular file: {path}")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RecordError("invalid result JSON") from exc
    if not isinstance(result, dict) or result.get("schema_version") != 1:
        raise RecordError("unsupported result schema")
    stack = result.get("stack", "")
    commit = result.get("candidate_commit", "")
    tooling = result.get("tooling_commit", "")
    if not STACK.fullmatch(stack) or not COMMIT.fullmatch(commit) or not COMMIT.fullmatch(tooling):
        raise RecordError("result contains an invalid stack or commit identity")
    outcome = result.get("result")
    rollback = result.get("rollback_result")
    if outcome not in OUTCOMES or rollback not in OUTCOMES[outcome]:
        raise RecordError("inconsistent terminal and rollback results")
    checks = result_checks(repo, history_ref, commit, tooling)
    contract = git_blob(repo, commit, f"stacks/{stack}/stack.yml") if checks["candidate_commit_available"] else None
    manifest = git_blob(repo, commit, f"stacks/{stack}/MANIFEST.tsv") if checks["candidate_commit_available"] else None
    checks["contract_matches_git"] = None if not checks["candidate_commit_available"] else (
        contract is not None and result.get("stack_contract_id") == f"sha256:{hashlib.sha256(contract).hexdigest()}"
    )
    checks["manifest_matches_git"] = None if not checks["candidate_commit_available"] else (
        manifest is not None and result.get("manifest_id") == f"sha256:{hashlib.sha256(manifest).hexdigest()}"
    )
    target_id = result.get("target_id", "")
    checks["target_id_well_formed"] = (
        isinstance(target_id, str) and target_id.startswith("sha256:") and valid_hash(target_id[7:])
    )
    status, failures, unknown = disposition(checks)
    return {
        "schema_version": 1,
        "record_type": "terminal_result",
        "stack": stack,
        "candidate_commit": commit,
        "history_ref": history_ref,
        "transaction_result": outcome,
        "rollback_result": rollback,
        "status": status,
        "checks": checks,
        "failures": failures,
        "unknown": unknown,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--record", type=Path)
    source.add_argument("--result-file", type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--history-ref", default="origin/main")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.result_file and args.receipt:
        raise RecordError("--receipt applies only to an accepted record")
    report = (
        compare_result(args.result_file, args.repo, args.history_ref)
        if args.result_file else compare(args.record, args.repo, args.history_ref, args.receipt)
    )
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        outcome = f" result={report['transaction_result']} rollback={report['rollback_result']}" if args.result_file else ""
        print(f"{report['status']}: {report['stack']} {report['candidate_commit']}{outcome}")
        for name in report["failures"] + report["unknown"]:
            print(f"- {name}: {report['checks'][name]}")
    return {"MATCH": 0, "MISMATCH": 1, "UNVERIFIABLE": 2}[report["status"]]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RecordError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
