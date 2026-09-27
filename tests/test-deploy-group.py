#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "deploy-group.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("deploy_group", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hosts = ("web-a", "web-b", "web-c")
    hostvars = {
        name: {
            "ansible_connection": "ssh",
            "ansible_host": f"{name}.example.invalid",
            "ansible_user": "operator",
            "homelab_environment": "production",
            "homelab_expected_hostname": f"{name}.example.invalid",
            "homelab_expected_machine_id": None,
        }
        for name in hosts
    }
    inventory = {
        "_meta": {"hostvars": hostvars},
        "production": {"children": ["web"]},
        "web": {"hosts": list(hosts)},
    }
    mapping = {"stacks": {"dozzle": {
        "group": "production", "hosts": list(hosts), "canary": "web-a",
    }}}
    assert [name for name, _ in module.select_targets(inventory, mapping, "dozzle", "canary")] == list(hosts)
    lab_inventory = json.loads(json.dumps(inventory))
    for values in lab_inventory["_meta"]["hostvars"].values():
        values["homelab_environment"] = "lab"
    assert [name for name, _ in module.select_targets(
        lab_inventory, mapping, "dozzle", "canary", "lab"
    )] == list(hosts)
    lab_inventory["_meta"]["hostvars"]["web-b"]["ansible_connection"] = "local"
    try:
        module.select_targets(lab_inventory, mapping, "dozzle", "serial", "lab")
    except module.GroupError as exc:
        assert "Grouped Lab targets must use the ssh connection plugin" in str(exc)
    else:
        raise AssertionError("grouped Lab accepted a local connection")
    if shutil.which("ansible-inventory"):
        example_inventory = module.load_inventory(
            ROOT / "ansible/inventory/production/hosts.example.yml"
        )
        example_inventory["_meta"]["hostvars"]["production-host"]["homelab_expected_hostname"] = "example.invalid"
        example_mapping = yaml.safe_load(
            (ROOT / "ansible/inventory/production/stack-targets.example.yml")
            .read_text(encoding="utf-8")
        )
        assert [name for name, _ in module.select_targets(
            example_inventory, example_mapping, "dozzle", "canary"
        )] == ["production-host"]
    assert module.classify_failure("one PRE_MUTATION_REFUSAL then REJECTED_ROLLBACK_VERIFIED") == "REJECTED_ROLLBACK_VERIFIED"
    assert module.classify_failure("unknown failure") == "FAILED_UNCLASSIFIED"

    wrong = {"stacks": {"dozzle": {"group": "web", "hosts": ["web-b"], "canary": "web-a"}}}
    try:
        module.select_targets(inventory, wrong, "dozzle", "canary")
    except module.GroupError:
        pass
    else:
        raise AssertionError("canary outside the first position was accepted")

    duplicate = json.loads(json.dumps(inventory))
    duplicate["_meta"]["hostvars"]["web-b"]["homelab_expected_hostname"] = hostvars["web-a"]["homelab_expected_hostname"]
    try:
        module.select_targets(duplicate, mapping, "dozzle", "serial")
    except module.GroupError:
        pass
    else:
        raise AssertionError("duplicate declared target identity was accepted")

    with tempfile.TemporaryDirectory(prefix="blueprint-group-test.") as raw_tmp:
        directory = Path(raw_tmp)
        inventory_path = directory / "hosts.yml"
        targets_path = directory / "targets.yml"
        inventory_path.write_text("---\nall: {}\n", encoding="utf-8")
        targets_path.write_text(yaml.safe_dump(mapping), encoding="utf-8")
        args = argparse.Namespace(
            inventory=inventory_path, targets=targets_path,
            stack="dozzle", mode="canary", environment="production", check=False, ref="HEAD",
        )
        original_load = module.load_inventory
        original_run = module.run_host
        calls: list[str] = []
        module.load_inventory = lambda path: inventory

        def fake_run(stack, alias, values, check, git_ref, temp_root, environment):
            assert environment == "production"
            calls.append(alias)
            return {
                "host": alias,
                "result": "ACCEPTED" if alias == "web-a" else "REJECTED_ROLLBACK_VERIFIED",
                "exit_code": 0 if alias == "web-a" else 1,
            }

        module.run_host = fake_run
        try:
            report = module.deploy(args)
        finally:
            module.load_inventory = original_load
            module.run_host = original_run
        assert calls == ["web-a", "web-b"]
        assert report["group_result"] == "PARTIAL"
        assert report["environment"] == "production"
        assert [item["result"] for item in report["targets"]] == [
            "ACCEPTED", "REJECTED_ROLLBACK_VERIFIED", "SKIPPED",
        ]
        output = directory / "result.json"
        module.atomic_json(output, report)
        assert json.loads(output.read_text()) == report

        calls_seen = []

        class FakeProcess:
            stdout = ["ACCEPTED: synthetic host\n"]

            def wait(self):
                return 0

        original_popen = module.subprocess.Popen

        def fake_popen(command, **kwargs):
            calls_seen.append((command, kwargs["env"]))
            return FakeProcess()

        module.subprocess.Popen = fake_popen
        try:
            result = module.run_host(
                "dozzle", "web-a", lab_inventory["_meta"]["hostvars"]["web-a"],
                False, "HEAD", directory, "lab",
            )
        finally:
            module.subprocess.Popen = original_popen
        assert result["result"] == "ACCEPTED"
        assert calls_seen[0][0][3:5] == ["--inventory", "lab"]
        assert calls_seen[0][1]["HOMELAB_LAB_HOSTNAME"] == "web-a.example.invalid"

    print("Group rollout tests passed: explicit selection, canary ordering, strict SSH Lab, partial stop and per-host JSON.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
