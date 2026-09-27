#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "report-config-drift.py"


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True, capture_output=True
    ).stdout


def main() -> int:
    spec = importlib.util.spec_from_file_location("config_drift", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    commit = git("rev-parse", "HEAD").decode().strip()
    contract = git("show", f"{commit}:stacks/dozzle/stack.yml")
    manifest = git("show", f"{commit}:stacks/dozzle/MANIFEST.tsv")
    with tempfile.TemporaryDirectory(prefix="blueprint-config-drift.") as raw_tmp:
        root = Path(raw_tmp)
        snapshot = root / "snapshot"
        deployed = snapshot / "opt/homelab-ops/stacks/dozzle"
        deployed.mkdir(parents=True)
        compose = deployed / "docker-compose.yml"
        defaults = deployed / "defaults.env"
        compose.write_bytes(git("show", f"{commit}:stacks/dozzle/compose.yaml"))
        defaults.write_bytes(git("show", f"{commit}:stacks/dozzle/defaults.env"))
        record = root / "dozzle.record"
        record.write_text("\n".join((
            "stack=dozzle",
            f"commit={commit}",
            f"tooling_commit={commit}",
            f"contract_hash={hashlib.sha256(contract).hexdigest()}",
            f"manifest_hash={hashlib.sha256(manifest).hexdigest()}",
            "target=/opt/homelab-ops/stacks/dozzle",
        )) + "\n", encoding="utf-8")
        clean = module.report(record, ROOT, "HEAD", snapshot)
        assert clean["status"] == "MATCH"
        assert clean["record_status"] == "MATCH"
        assert clean["current_runtime"] == "NOT_CHECKED"
        assert len(clean["files"]) == 2
        assert all(item["state"] == "MATCH" for item in clean["files"])

        defaults.write_text("changed\n", encoding="utf-8")
        changed = module.report(record, ROOT, "HEAD", snapshot)
        assert changed["status"] == "DRIFT"
        assert [item["state"] for item in changed["files"]] == ["MATCH", "DIFFERENT"]
        defaults.unlink()
        missing = module.report(record, ROOT, "HEAD", snapshot)
        assert [item["state"] for item in missing["files"]] == ["MATCH", "MISSING"]

        outside = root / "outside.env"
        outside.write_text("outside\n", encoding="utf-8")
        try:
            defaults.symlink_to(outside)
        except (OSError, NotImplementedError):
            pass
        else:
            unsafe = module.report(record, ROOT, "HEAD", snapshot)
            assert [item["state"] for item in unsafe["files"]] == ["MATCH", "UNSAFE"]
            defaults.unlink()

        record.write_text(record.read_text().replace(
            f"contract_hash={hashlib.sha256(contract).hexdigest()}",
            f"contract_hash={'0' * 64}",
        ), encoding="utf-8")
        mismatch = module.report(record, ROOT, "HEAD", snapshot)
        assert mismatch["status"] == "RECORD_MISMATCH"
        assert mismatch["files"] == []

    print("Read-only configuration drift tests passed: exact bytes, changed, missing, unsafe and record mismatch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
