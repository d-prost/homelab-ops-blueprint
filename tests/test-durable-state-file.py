#!/usr/bin/env python3
from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "durable-state-file.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        text=True,
        capture_output=True,
    )


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    source = root / "source"
    destination = root / "accepted.record"
    source.write_text("new-record\n", encoding="utf-8")
    destination.write_text("old-record\n", encoding="utf-8")

    failed = run(
        "commit",
        "--source",
        str(source),
        "--destination",
        str(destination),
        "--mode",
        "0640",
        "--test-fail-before-rename",
    )
    if failed.returncode == 0:
        raise AssertionError("injected pre-rename failure unexpectedly succeeded")
    if destination.read_text(encoding="utf-8") != "old-record\n":
        raise AssertionError("failed commit replaced the durable destination")
    leftovers = list(root.glob(".accepted.record.*"))
    if leftovers:
        raise AssertionError(f"failed commit left temporary files: {leftovers!r}")

    committed = run(
        "commit",
        "--source",
        str(source),
        "--destination",
        str(destination),
        "--mode",
        "0640",
    )
    if committed.returncode:
        raise AssertionError(committed.stdout + committed.stderr)
    if destination.read_text(encoding="utf-8") != "new-record\n":
        raise AssertionError("atomic commit did not replace destination")
    if stat.S_IMODE(destination.stat().st_mode) != 0o640:
        raise AssertionError("atomic commit did not preserve requested mode")

    removed = run("remove", "--path", str(destination))
    if removed.returncode:
        raise AssertionError(removed.stdout + removed.stderr)
    if destination.exists():
        raise AssertionError("durable remove did not unlink destination")

print(
    "Durable state-file tests passed: injected pre-rename failure preserved the "
    "old record, successful commit replaced it atomically, and removal succeeded."
)
