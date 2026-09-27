#!/usr/bin/env python3
"""Compare a copied target file tree with the last accepted Git payload."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path, PurePosixPath

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPARATOR = ROOT / "scripts" / "compare-deployment-record.py"


class DriftError(RuntimeError):
    pass


def load_comparator():
    spec = importlib.util.spec_from_file_location("record_comparator", COMPARATOR)
    if spec is None or spec.loader is None:
        raise DriftError("deployment record comparator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def relative_file(value: str, label: str) -> PurePosixPath:
    if (not isinstance(value, str) or not value or value.startswith("/")
            or "\\" in value or "//" in value or any(
                part in {".", ".."} for part in value.split("/")
            )):
        raise DriftError(f"{label} is not a safe relative path")
    path = PurePosixPath(value)
    if any(part in {".", ".."} for part in path.parts) or value.endswith("/"):
        raise DriftError(f"{label} is not a safe relative path")
    return path


def target_path(value: str, stack: str) -> PurePosixPath:
    if (not isinstance(value, str) or "//" in value or "\\" in value
            or any(part in {".", ".."} for part in value.split("/"))):
        raise DriftError("accepted target path is unsafe")
    path = PurePosixPath(value)
    if (not path.is_absolute() or any(part in {".", ".."} for part in path.parts)
            or len(path.parts) < 5 or path.parts[1] not in {"opt", "srv"}
            or path.parts[2:4] != ("homelab-ops", "stacks") or path.parts[4] != stack):
        raise DriftError("accepted target path is outside the stack root")
    return path


def report(record_path: Path, repo: Path, history_ref: str, snapshot_root: Path,
           receipt_path: Path | None = None) -> dict:
    comparator = load_comparator()
    provenance = comparator.compare(record_path, repo, history_ref, receipt_path)
    if provenance["status"] != "MATCH":
        return {
            "schema_version": 1,
            "status": "RECORD_" + provenance["status"],
            "record_status": provenance["status"],
            "files": [],
            "current_runtime": "NOT_CHECKED",
        }
    record = comparator.parse_kv(record_path)
    stack = record["stack"]
    commit = record["commit"]
    contract_blob = comparator.git_blob(repo, commit, f"stacks/{stack}/stack.yml")
    manifest_blob = comparator.git_blob(repo, commit, f"stacks/{stack}/MANIFEST.tsv")
    if contract_blob is None or manifest_blob is None:
        raise DriftError("accepted Git payload is unavailable")
    contract = yaml.safe_load(contract_blob)
    if not isinstance(contract, dict):
        raise DriftError("accepted stack contract is malformed")
    target = target_path(contract.get("stack_target_dir"), stack)
    if record.get("target") != str(target):
        raise DriftError("record target differs from accepted Git contract")
    if not snapshot_root.is_dir() or snapshot_root.is_symlink():
        raise DriftError("snapshot root must be a real directory")
    root = snapshot_root.resolve(strict=True)
    files: list[dict] = []
    destinations: set[str] = set()
    for line in manifest_blob.decode("utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 2:
            raise DriftError("accepted manifest is malformed")
        source = relative_file(fields[0], "manifest source")
        destination = fields[1]
        if not destination.startswith(str(target) + "/") or destination in destinations:
            raise DriftError("accepted manifest destination is unsafe or repeated")
        relative_destination = relative_file(destination[len(str(target)) + 1:], "manifest destination")
        destinations.add(destination)
        expected_blob = comparator.git_blob(repo, commit, f"stacks/{stack}/{source}")
        if expected_blob is None:
            raise DriftError("accepted Git payload has a missing managed file")
        expected_hash = hashlib.sha256(expected_blob).hexdigest()
        actual = root.joinpath(*target.parts[1:], *relative_destination.parts)
        resolved = actual.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError:
            state = "UNSAFE"
            actual_hash = None
        else:
            if actual.is_symlink():
                state, actual_hash = "UNSAFE", None
            elif not actual.exists():
                state, actual_hash = "MISSING", None
            elif not actual.is_file():
                state, actual_hash = "UNSAFE", None
            else:
                actual_hash = hashlib.sha256(actual.read_bytes()).hexdigest()
                state = "MATCH" if actual_hash == expected_hash else "DIFFERENT"
        files.append({
            "destination": destination,
            "state": state,
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
        })
    if not files:
        raise DriftError("accepted manifest has no managed files")
    status = "MATCH" if all(item["state"] == "MATCH" for item in files) else "DRIFT"
    return {
        "schema_version": 1,
        "stack": stack,
        "accepted_commit": commit,
        "status": status,
        "record_status": "MATCH",
        "files": files,
        "current_runtime": "NOT_CHECKED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--history-ref", default="origin/main")
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = report(args.record, args.repo, args.history_ref, args.snapshot_root, args.receipt)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"{result['status']}: accepted configuration; current runtime {result['current_runtime']}")
        for item in result["files"]:
            if item["state"] != "MATCH":
                print(f"- {item['state']}: {item['destination']}")
    return 0 if result["status"] == "MATCH" else 1 if result["status"] == "DRIFT" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DriftError, OSError, UnicodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
