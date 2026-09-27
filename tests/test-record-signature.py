#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sign-deployment-record.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("record_signature", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="blueprint-record-signature.") as raw_tmp:
        root = Path(raw_tmp)
        key = root / "signing-key"
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
            check=True, capture_output=True,
        )
        allowed = root / "allowed_signers"
        allowed.write_text("operator " + key.with_suffix(".pub").read_text(encoding="utf-8"), encoding="utf-8")
        record = root / "dozzle.record"
        record.write_text(
            "stack=dozzle\ncommit=" + "1" * 40 + "\nverified=functional\n",
            encoding="utf-8",
        )
        signature = root / "dozzle.record.sig"
        module.sign(record, key, signature)
        module.verify(record, signature, allowed, "operator")
        try:
            module.sign(record, key, signature)
        except module.SignatureError as exc:
            assert "already exists" in str(exc)
        else:
            raise AssertionError("signature was overwritten")
        try:
            module.verify(record, signature, allowed, "wrong-operator")
        except module.SignatureError:
            pass
        else:
            raise AssertionError("wrong signer identity was accepted")
        record.write_text(record.read_text(encoding="utf-8") + "target=/changed\n", encoding="utf-8")
        try:
            module.verify(record, signature, allowed, "operator")
        except module.SignatureError:
            pass
        else:
            raise AssertionError("modified record was accepted")
    print("Optional SSH record-signature tests passed: exact bytes, signer identity and tampering.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
