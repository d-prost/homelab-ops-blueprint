#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

SAFE_HOSTNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")
MACHINE_ID = re.compile(r"^[0-9a-f]{32}$")
UNSAFE_SSH = (
    re.compile(r"StrictHostKeyChecking\s*=\s*(?:no|accept-new)", re.IGNORECASE),
    re.compile(r"UserKnownHostsFile\s*=\s*/dev/null", re.IGNORECASE),
    re.compile(r"GlobalKnownHostsFile\s*=\s*/dev/null", re.IGNORECASE),
)
FALSE_VALUES = {False, 0, "0", "false", "False", "no", "No", "off", "Off"}


class InventoryError(RuntimeError):
    pass


def inventory_hostvars(path: Path) -> dict[str, dict]:
    try:
        result = subprocess.run(
            ["ansible-inventory", "-i", str(path), "--list"],
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise InventoryError("ansible-inventory is required") from exc
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise InventoryError(f"cannot resolve inventory: {detail}")
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InventoryError("ansible-inventory returned invalid JSON") from exc
    hostvars = document.get("_meta", {}).get("hostvars", {})
    if not isinstance(hostvars, dict) or not hostvars:
        raise InventoryError("inventory resolves to zero hosts")
    return hostvars


def validate_host(name: str, values: dict, environment: str) -> None:
    if values.get("homelab_environment") != environment:
        raise InventoryError(
            f"{name}: homelab_environment must be exactly {environment!r}"
        )

    expected_hostname = values.get("homelab_expected_hostname")
    if (
        not isinstance(expected_hostname, str)
        or not expected_hostname
        or not SAFE_HOSTNAME.fullmatch(expected_hostname)
    ):
        raise InventoryError(f"{name}: homelab_expected_hostname is required and unsafe")

    expected_machine_id = values.get("homelab_expected_machine_id")
    if expected_machine_id is not None and (
        not isinstance(expected_machine_id, str)
        or not MACHINE_ID.fullmatch(expected_machine_id)
    ):
        raise InventoryError(
            f"{name}: homelab_expected_machine_id must be null or 32 lowercase hex characters"
        )

    if environment != "production":
        return

    connection = values.get("ansible_connection", "ssh")
    if connection != "ssh":
        raise InventoryError(
            f"{name}: Production targets must use the ssh connection plugin, got {connection!r}"
        )

    host_key_setting = values.get("ansible_host_key_checking")
    if host_key_setting in FALSE_VALUES:
        raise InventoryError(f"{name}: Production host-key checking must not be disabled")

    for key in ("ansible_ssh_args", "ansible_ssh_common_args", "ansible_ssh_extra_args"):
        value = values.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise InventoryError(f"{name}: {key} must be a string when configured")
        for pattern in UNSAFE_SSH:
            if pattern.search(value):
                raise InventoryError(
                    f"{name}: {key} weakens SSH host-key verification: {value!r}"
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--environment", choices=("production", "lab"), required=True)
    args = parser.parse_args()

    if not args.inventory.is_file():
        raise InventoryError(f"inventory is not readable: {args.inventory}")

    hostvars = inventory_hostvars(args.inventory)
    for name, values in sorted(hostvars.items()):
        if not isinstance(values, dict):
            raise InventoryError(f"{name}: host variables must be a mapping")
        validate_host(name, values, args.environment)

    print(
        f"Target inventory identity guard passed: {len(hostvars)} "
        f"{args.environment} host(s)."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InventoryError as exc:
        raise SystemExit(f"ERROR: PRE_MUTATION_REFUSAL: {exc}")
