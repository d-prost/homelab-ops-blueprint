#!/usr/bin/env python3
"""Serial or canary rollout through the existing single-target transaction path."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
SAFE_STACK = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
RESULT_MARKERS = (
    "ACCEPTANCE_PERSISTENCE_FAILED",
    "REJECTED_ROLLBACK_FAILED",
    "REJECTED_ROLLBACK_VERIFIED",
    "INTERRUPTED_UNRESOLVED",
    "PRE_MUTATION_REFUSAL",
)


class GroupError(RuntimeError):
    pass


def load_inventory_validator():
    path = ROOT / "scripts" / "validate-target-inventory.py"
    spec = importlib.util.spec_from_file_location("target_inventory", path)
    if spec is None or spec.loader is None:
        raise GroupError("target inventory validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_inventory(path: Path) -> dict:
    result = subprocess.run(
        ["ansible-inventory", "-i", str(path), "--list"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise GroupError("cannot resolve target inventory")
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise GroupError("Ansible inventory returned invalid JSON") from exc
    if not isinstance(document, dict):
        raise GroupError("Ansible inventory must be an object")
    return document


def group_members(document: dict, group: str) -> set[str]:
    if not SAFE_NAME.fullmatch(group) or group == "_meta" or group not in document:
        raise GroupError("selected inventory group is missing or unsafe")
    visited: set[str] = set()
    members: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        value = document.get(name)
        if not isinstance(value, dict):
            raise GroupError("inventory group is malformed")
        hosts = value.get("hosts") or []
        children = value.get("children") or []
        if not isinstance(hosts, list) or not isinstance(children, list):
            raise GroupError("inventory group members are malformed")
        for host in hosts:
            if not isinstance(host, str) or not SAFE_NAME.fullmatch(host):
                raise GroupError("inventory contains an unsafe host alias")
            members.add(host)
        for child in children:
            if not isinstance(child, str) or not SAFE_NAME.fullmatch(child) or child == "_meta":
                raise GroupError("inventory contains an unsafe child group")
            visit(child)

    visit(group)
    return members


def select_targets(document: dict, mapping: dict, stack: str, mode: str,
                   environment: str = "production") -> list[tuple[str, dict]]:
    if not SAFE_STACK.fullmatch(stack):
        raise GroupError("unsafe stack name")
    stacks = mapping.get("stacks")
    if not isinstance(stacks, dict) or stack not in stacks:
        raise GroupError("stack is not explicitly mapped to hosts")
    selection = stacks[stack]
    if not isinstance(selection, dict) or set(selection) - {"group", "hosts", "canary"}:
        raise GroupError("stack target selection has unsupported fields")
    group = selection.get("group")
    hosts = selection.get("hosts")
    if not isinstance(group, str) or not isinstance(hosts, list) or not hosts:
        raise GroupError("stack must name a group and non-empty ordered hosts")
    if any(not isinstance(host, str) or not SAFE_NAME.fullmatch(host) for host in hosts):
        raise GroupError("stack target list contains an unsafe host alias")
    if len(hosts) != len(set(hosts)):
        raise GroupError("stack target list contains duplicate host aliases")
    members = group_members(document, group)
    if not set(hosts).issubset(members):
        raise GroupError("stack target list includes a host outside its declared group")
    if mode == "canary" and (selection.get("canary") != hosts[0]):
        raise GroupError("canary mode requires the declared canary to be the first ordered host")
    hostvars = document.get("_meta", {}).get("hostvars", {})
    if not isinstance(hostvars, dict):
        raise GroupError("inventory hostvars are malformed")
    validator = load_inventory_validator()
    try:
        validator.validate_environment_ssh_args()
    except validator.InventoryError as exc:
        raise GroupError(str(exc)) from exc
    selected: list[tuple[str, dict]] = []
    identities: set[str] = set()
    for host in hosts:
        values = hostvars.get(host)
        if not isinstance(values, dict):
            raise GroupError(f"{host}: resolved host variables are missing")
        try:
            validator.validate_host(host, values, environment, require_ssh=True)
        except validator.InventoryError as exc:
            raise GroupError(str(exc)) from exc
        hostname = values["homelab_expected_hostname"]
        if hostname in identities:
            raise GroupError("multiple aliases declare the same target hostname")
        identities.add(hostname)
        selected.append((host, values))
    return selected


def classify_failure(output: str) -> str:
    latest = max(((output.rfind(marker), marker) for marker in RESULT_MARKERS), default=(-1, ""))
    return latest[1] if latest[0] >= 0 else "FAILED_UNCLASSIFIED"


def atomic_json(path: Path, document: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw_temp)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(document, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def run_host(stack: str, alias: str, values: dict, check: bool, git_ref: str,
             temp_root: Path, environment: str = "production") -> dict:
    inventory = temp_root / f"{alias}.yml"
    inventory.write_text(yaml.safe_dump({"all": {"hosts": {alias: values}}}, sort_keys=False), encoding="utf-8")
    inventory.chmod(0o600)
    command = [
        "bash", str(ROOT / "scripts" / "deploy-stack.sh"), stack,
        "--inventory", environment, "--inventory-file", str(inventory),
    ]
    if check:
        command.append("--check")
    if git_ref != "HEAD":
        command.extend(["--ref", git_ref])
    print(f"TARGET {alias}: starting {'check' if check else 'deployment'}", flush=True)
    command_env = os.environ.copy()
    if environment == "lab":
        command_env["HOMELAB_LAB_HOSTNAME"] = values["homelab_expected_hostname"]
    process = subprocess.Popen(
        command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, env=command_env,
    )
    output_parts: list[str] = []
    output_length = 0
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        output_parts.append(line)
        output_length += len(line)
        if output_length > 200_000:
            output_parts = output_parts[-200:]
            output_length = sum(map(len, output_parts))
    returncode = process.wait()
    result = "CHECK_PASSED" if check else "ACCEPTED" if returncode == 0 else classify_failure("".join(output_parts))
    if returncode and result in {"CHECK_PASSED", "ACCEPTED"}:
        result = classify_failure("".join(output_parts))
    return {"host": alias, "result": result, "exit_code": returncode}


def deploy(args: argparse.Namespace) -> dict:
    if not args.inventory.is_file() or not args.targets.is_file():
        raise GroupError("inventory and stack-target mapping must be readable files")
    mapping = yaml.safe_load(args.targets.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict) or set(mapping) != {"stacks"}:
        raise GroupError("stack-target mapping must contain only a stacks object")
    document = load_inventory(args.inventory)
    selected = select_targets(document, mapping, args.stack, args.mode, args.environment)
    report = {
        "schema_version": 1,
        "stack": args.stack,
        "mode": args.mode,
        "environment": args.environment,
        "check_mode": args.check,
        "group_result": "PENDING",
        "targets": [],
    }
    with tempfile.TemporaryDirectory(prefix="blueprint-group.") as raw_temp:
        temp_root = Path(raw_temp)
        temp_root.chmod(0o700)
        failed = False
        for alias, values in selected:
            if failed:
                report["targets"].append({"host": alias, "result": "SKIPPED", "reason": "previous host failed"})
                continue
            try:
                host_result = run_host(args.stack, alias, values, args.check, args.ref, temp_root, args.environment)
            except OSError:
                host_result = {"host": alias, "result": "FAILED_UNCLASSIFIED", "exit_code": 1}
            report["targets"].append(host_result)
            failed = host_result["exit_code"] != 0 or host_result["result"] not in {"ACCEPTED", "CHECK_PASSED"}
    successes = sum(item["result"] in {"ACCEPTED", "CHECK_PASSED"} for item in report["targets"])
    report["group_result"] = "COMPLETE" if not failed else "PARTIAL" if successes else "FAILED"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stack")
    parser.add_argument("--inventory", type=Path, default=ROOT / "ansible/inventory/production/hosts.yml")
    parser.add_argument("--targets", type=Path, default=ROOT / "ansible/inventory/production/stack-targets.yml")
    parser.add_argument("--mode", choices=("serial", "canary"), default="serial")
    parser.add_argument("--environment", choices=("production", "lab"), default="production")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    output = args.output or ROOT / "reports" / f"group-{args.stack}-{uuid.uuid4().hex}.json"
    report = deploy(args)
    atomic_json(output, report)
    print(f"GROUP_RESULT={report['group_result']} RESULT_JSON={output}")
    return 0 if report["group_result"] == "COMPLETE" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GroupError, OSError, yaml.YAMLError) as exc:
        print(f"ERROR: PRE_MUTATION_REFUSAL: {exc}", file=sys.stderr)
        raise SystemExit(2)
