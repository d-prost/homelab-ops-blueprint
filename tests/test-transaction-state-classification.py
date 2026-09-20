#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "classify-transaction-state.py"
TX = "tx-123"
CANDIDATE = "1" * 40
PREVIOUS = "2" * 40
PREVIOUS_RECORD_ID = "3" * 64


def write_marker(path: Path, phase: str, previous: bool = True) -> None:
    path.write_text(
        "\n".join(
            [
                f"transaction_id={TX}",
                "stack=dozzle",
                f"candidate_commit={CANDIDATE}",
                f"previous_accepted_commit={PREVIOUS if previous else ''}",
                f"previous_record_id={PREVIOUS_RECORD_ID if previous else ''}",
                f"phase={phase}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def classify(root: Path) -> list[str]:
    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--stack",
            "dozzle",
            "--marker",
            str(root / "marker"),
            "--record",
            str(root / "record"),
            "--receipt",
            str(root / "receipt"),
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout.strip().split("|")


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    fields = classify(root)
    if fields[0] != "NONE":
        raise AssertionError(fields)

    write_marker(root / "marker", "PREPARED", previous=False)
    if classify(root)[0] != "CLEANUP":
        raise AssertionError("PREPARED must clean without rollback")

    write_marker(root / "marker", "MUTATING")
    if classify(root)[0] != "RESTORE":
        raise AssertionError("MUTATING with previous accepted state must restore")

    write_marker(root / "marker", "RESTORING")
    if classify(root)[0] != "RESTORE":
        raise AssertionError("RESTORING must be idempotently retried")

    write_marker(root / "marker", "MUTATING", previous=False)
    if classify(root)[0] != "MANUAL":
        raise AssertionError("first-deploy MUTATING interruption must remain manual")

    write_marker(root / "marker", "ACCEPTANCE_PERSISTENCE_FAILED")
    if classify(root)[0] != "MANUAL":
        raise AssertionError("acceptance persistence failure must remain manual")

    write_marker(root / "marker", "ACCEPTANCE_PENDING")
    record = (
        "stack=dozzle\n"
        f"commit={CANDIDATE}\n"
        f"transaction_id={TX}\n"
        "verified=functional\n"
    )
    (root / "record").write_text(record, encoding="utf-8")
    record_hash = hashlib.sha256(record.encode("utf-8")).hexdigest()
    (root / "receipt").write_text(
        f"transaction_id={TX}\nrecord_sha256={record_hash}\n",
        encoding="utf-8",
    )
    fields = classify(root)
    if fields[0] != "ACCEPTED_STALE" or fields[6] != record_hash:
        raise AssertionError(fields)

    (root / "receipt").write_text(
        f"transaction_id=other\nrecord_sha256={record_hash}\n",
        encoding="utf-8",
    )
    if classify(root)[0] != "MANUAL":
        raise AssertionError("receipt transaction mismatch must remain manual")

    (root / "receipt").write_text(
        f"transaction_id={TX}\nrecord_sha256={'f' * 64}\n",
        encoding="utf-8",
    )
    if classify(root)[0] != "MANUAL":
        raise AssertionError("receipt record hash mismatch must remain manual")

print(
    "Transaction-state classification tests passed: PREPARED cleanup, "
    "MUTATING/RESTORING recovery, conservative manual ambiguity and durable "
    "acceptance receipt proof."
)
