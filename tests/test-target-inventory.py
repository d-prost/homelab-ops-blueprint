#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-target-inventory.py"


def write_inventory(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def run(path: Path, environment: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(VALIDATOR), str(path), "--environment", environment],
        text=True,
        capture_output=True,
    )


def expect_ok(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


def expect_fail(result: subprocess.CompletedProcess[str], text: str) -> None:
    if result.returncode == 0:
        raise AssertionError("expected target-inventory validation failure")
    combined = result.stdout + result.stderr
    if "PRE_MUTATION_REFUSAL" not in combined or text not in combined:
        raise AssertionError(combined)


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    inventory = root / "hosts.yml"

    write_inventory(
        inventory,
        """---
all:
  hosts:
    prod:
      ansible_connection: ssh
      ansible_host: 192.0.2.10
      ansible_user: operator
      homelab_environment: production
      homelab_expected_hostname: prod.example
      homelab_expected_machine_id: null
""",
    )
    expect_ok(run(inventory, "production"))

    write_inventory(
        inventory,
        """---
all:
  hosts:
    prod:
      ansible_connection: local
      ansible_host: 127.0.0.1
      homelab_environment: production
      homelab_expected_hostname: prod.example
""",
    )
    expect_fail(run(inventory, "production"), "must use the ssh connection plugin")

    write_inventory(
        inventory,
        """---
all:
  hosts:
    prod:
      ansible_connection: ssh
      ansible_host: 192.0.2.10
      ansible_user: operator
      ansible_ssh_common_args: "-o StrictHostKeyChecking=no"
      homelab_environment: production
      homelab_expected_hostname: prod.example
""",
    )
    expect_fail(run(inventory, "production"), "weakens SSH host-key verification")

    write_inventory(
        inventory,
        """---
all:
  hosts:
    prod:
      ansible_connection: ssh
      ansible_host: 192.0.2.10
      ansible_user: operator
      homelab_environment: production
      homelab_expected_hostname: prod.example
      homelab_expected_machine_id: NOT-A-MACHINE-ID
""",
    )
    expect_fail(run(inventory, "production"), "must be null or 32 lowercase hex")

    write_inventory(
        inventory,
        """---
all:
  hosts:
    lab:
      ansible_connection: local
      ansible_host: 127.0.0.1
      homelab_environment: lab
      homelab_expected_hostname: disposable-lab
""",
    )
    expect_ok(run(inventory, "lab"))

print(
    "Target inventory policy tests passed: Production SSH is mandatory, "
    "host-key weakening is refused, machine ID is optional and validated."
)
