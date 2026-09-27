#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "write-deployment-result.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("deployment_result", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = argparse.Namespace(
        stack="dozzle",
        transaction_id="synthetic-1",
        candidate_commit="a" * 40,
        tooling_commit="b" * 40,
        previous_commit="",
        previous_record_id="",
        contract_hash="c" * 64,
        manifest_hash="d" * 64,
        target_hostname="example-target",
        target_machine_id="",
        result="REJECTED_ROLLBACK_VERIFIED",
        rollback_result="VERIFIED",
    )
    with tempfile.TemporaryDirectory(prefix="blueprint-result-test.") as raw_tmp:
        destination = Path(raw_tmp) / "records" / "dozzle.result.json"
        report = module.make_report(args)
        module.atomic_write(destination, report)
        assert json.loads(destination.read_text()) == report
        if os.name != "nt":
            assert destination.stat().st_mode & 0o777 == 0o640
        args.result = "ACCEPTED"
        args.rollback_result = "NOT_NEEDED"
        module.atomic_write(destination, module.make_report(args))
        assert json.loads(destination.read_text())["result"] == "ACCEPTED"
        args.rollback_result = "VERIFIED"
        try:
            module.make_report(args)
        except module.ResultError:
            pass
        else:
            raise AssertionError("inconsistent result and rollback status accepted")
        args.rollback_result = "NOT_NEEDED"
        args.stack = "../unsafe"
        try:
            module.make_report(args)
        except module.ResultError:
            pass
        else:
            raise AssertionError("unsafe stack name accepted")
    print("Deployment-result tests passed: durable replacement and outcome guards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
