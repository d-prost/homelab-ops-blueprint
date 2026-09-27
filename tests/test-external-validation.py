#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="blueprint-external-validator.") as raw_tmp:
        stack = Path(raw_tmp) / "other-repository" / "stacks" / "dozzle"
        shutil.copytree(ROOT / "stacks" / "dozzle", stack)
        command = [
            sys.executable, str(ROOT / "scripts" / "validate-stack-contracts.py"),
            "--stack-dir", str(stack), "--json",
        ]
        passed = subprocess.run(command, check=True, capture_output=True, text=True)
        result = json.loads(passed.stdout)
        assert result == {
            "schema_version": 1, "status": "PASS", "validated_stacks": ["dozzle"],
        }
        (stack / "MANIFEST.tsv").write_text("invalid\n", encoding="utf-8")
        failed = subprocess.run(command, check=False, capture_output=True, text=True)
        assert failed.returncode != 0
        assert "expected two TSV fields" in failed.stderr
    print("External stack validation tests passed: JSON success and invalid manifest refusal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
