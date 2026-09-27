#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare-deployment-record.py"


def run(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main() -> int:
    spec = importlib.util.spec_from_file_location("deployment_record", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    commit = run("rev-parse", "origin/main").decode().strip()
    stack = "dozzle"
    contract = run("show", f"{commit}:stacks/{stack}/stack.yml")
    manifest = run("show", f"{commit}:stacks/{stack}/MANIFEST.tsv")
    contract_hash = hashlib.sha256(contract).hexdigest()
    manifest_hash = hashlib.sha256(manifest).hexdigest()
    hostname = "example-target"
    target_hash = hashlib.sha256(f"{hostname}|".encode()).hexdigest()
    values = {
        "schema_version": "2",
        "stack": stack,
        "commit": commit,
        "tooling_commit": commit,
        "transaction_id": "synthetic-transaction",
        "contract_hash": contract_hash,
        "manifest_hash": manifest_hash,
        "stack_contract_id": f"sha256:{contract_hash}",
        "manifest_id": f"sha256:{manifest_hash}",
        "target_hostname": hostname,
        "target_machine_id": "",
        "target_id": f"sha256:{target_hash}",
        "verified": "functional",
        "verification_result": "PASS",
        "verification_result_id": f"sha256:{'a' * 64}",
    }
    with tempfile.TemporaryDirectory(prefix="blueprint-record-test.") as raw_tmp:
        directory = Path(raw_tmp)
        record = directory / "accepted.record"
        receipt = directory / "accepted.receipt"

        def write() -> None:
            record.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
            receipt.write_text(
                f"transaction_id={values['transaction_id']}\n"
                f"record_sha256={hashlib.sha256(record.read_bytes()).hexdigest()}\n",
                encoding="utf-8",
            )

        write()
        report = module.compare(record, ROOT, "origin/main", receipt)
        assert report["status"] == "MATCH", report
        values["contract_hash"] = "0" * 64
        write()
        report = module.compare(record, ROOT, "origin/main", receipt)
        assert report["status"] == "MISMATCH"
        assert "contract_matches_git" in report["failures"]
        values["contract_hash"] = contract_hash
        write()
        report = module.compare(record, ROOT, "missing-history-ref", receipt)
        assert report["status"] == "UNVERIFIABLE"
        assert report["checks"]["history_ref_available"] is False
        receipt.write_text("transaction_id=wrong\nrecord_sha256=" + "0" * 64 + "\n", encoding="utf-8")
        report = module.compare(record, ROOT, "origin/main", receipt)
        assert "receipt_matches" in report["failures"]
        legacy = {key: value for key, value in values.items() if key not in {
            "schema_version", "stack_contract_id", "manifest_id", "target_id",
            "verification_result", "verification_result_id",
        }}
        values = legacy
        write()
        assert module.compare(record, ROOT, "origin/main", receipt)["status"] == "MATCH"
        values["stack"] = "../unsafe"
        write()
        try:
            module.compare(record, ROOT, "origin/main", receipt)
        except module.RecordError:
            pass
        else:
            raise AssertionError("unsafe stack name was accepted")

    print("Deployment-record comparison tests passed: v1/v2, Git mismatch, history and receipt guards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
