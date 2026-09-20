#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "target-lock-key.py"


def run_inventory(body: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "hosts.yml"
        path.write_text(body, encoding="utf-8")
        return subprocess.run(
            ["python3", str(SCRIPT), str(path)],
            text=True,
            capture_output=True,
        )


def require_ok(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    value = result.stdout.strip()
    if len(value) != 64:
        raise AssertionError(f"unexpected lock key: {value!r}")
    return value


first = require_ok(
    run_inventory(
        """---
all:
  hosts:
    alias-one:
      ansible_connection: ssh
      ansible_host: first.example.invalid
      homelab_environment: production
      homelab_expected_hostname: target.example.invalid
"""
    )
)
second = require_ok(
    run_inventory(
        """---
all:
  hosts:
    completely-different-alias:
      ansible_connection: ssh
      ansible_host: second.example.invalid
      homelab_environment: production
      homelab_expected_hostname: target.example.invalid
"""
    )
)
if first != second:
    raise AssertionError("same declared target produced different host-global lock keys")

different_target = require_ok(
    run_inventory(
        """---
all:
  hosts:
    alias-one:
      ansible_connection: ssh
      ansible_host: first.example.invalid
      homelab_environment: production
      homelab_expected_hostname: another-target.example.invalid
"""
    )
)
if first == different_target:
    raise AssertionError("different declared targets produced the same lock key")

multi = run_inventory(
    """---
all:
  hosts:
    first:
      homelab_environment: production
      homelab_expected_hostname: first.example.invalid
    second:
      homelab_environment: production
      homelab_expected_hostname: second.example.invalid
"""
)
if multi.returncode == 0:
    raise AssertionError("multi-target inventory unexpectedly produced a v1 lock key")
combined = multi.stdout + multi.stderr
if "PRE_MUTATION_REFUSAL" not in combined or "exactly one inventory target" not in combined:
    raise AssertionError(combined)

print(
    "Target lock-key tests passed: aliases/runtime addresses do not split the "
    "same target lock, distinct targets separate, multi-target input is refused."
)
