#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


class LockKeyError(RuntimeError):
    pass


def load_hostvars(path: Path) -> dict[str, dict]:
    try:
        result = subprocess.run(
            ["ansible-inventory", "-i", str(path), "--list"],
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise LockKeyError("ansible-inventory is required") from exc
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise LockKeyError(f"cannot resolve inventory: {detail}")
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LockKeyError("ansible-inventory returned invalid JSON") from exc
    hostvars = document.get("_meta", {}).get("hostvars", {})
    if not isinstance(hostvars, dict) or len(hostvars) != 1:
        raise LockKeyError(
            f"v1 requires exactly one inventory target, resolved {len(hostvars) if isinstance(hostvars, dict) else 0}"
        )
    return hostvars


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()

    if not args.inventory.is_file():
        raise LockKeyError(f"inventory is not readable: {args.inventory}")

    hostvars = load_hostvars(args.inventory)
    _, values = next(iter(hostvars.items()))
    if not isinstance(values, dict):
        raise LockKeyError("inventory host variables must be a mapping")

    environment = values.get("homelab_environment")
    expected_hostname = values.get("homelab_expected_hostname")
    if environment not in {"production", "lab"}:
        raise LockKeyError("homelab_environment must be production or lab")
    if not isinstance(expected_hostname, str) or not expected_hostname:
        raise LockKeyError("homelab_expected_hostname is required")

    canonical = json.dumps(
        {
            "environment": environment,
            "expected_hostname": expected_hostname,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    print(hashlib.sha256(canonical).hexdigest())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LockKeyError as exc:
        raise SystemExit(f"ERROR: PRE_MUTATION_REFUSAL: {exc}")
