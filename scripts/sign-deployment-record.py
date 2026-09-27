#!/usr/bin/env python3
"""Sign or verify copied acceptance-record bytes using an operator SSH key."""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "homelab-ops-blueprint-record"
COMPARATOR = ROOT / "scripts" / "compare-deployment-record.py"


class SignatureError(RuntimeError):
    pass


def safe_file(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise SignatureError(f"{label} must be a regular file")
    return path.read_bytes()


def outside_repo(path: Path, label: str) -> None:
    try:
        path.resolve(strict=False).relative_to(ROOT.resolve())
    except ValueError:
        return
    raise SignatureError(f"{label} must stay outside the public repository")


def record_bytes(path: Path) -> bytes:
    raw = safe_file(path, "accepted record")
    spec = importlib.util.spec_from_file_location("record_comparator", COMPARATOR)
    if spec is None or spec.loader is None:
        raise SignatureError("record parser is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parsed = module.parse_kv(path)
    if not parsed.get("stack") or not parsed.get("commit") or parsed.get("verified") != "functional":
        raise SignatureError("file is not a functional accepted record")
    return raw


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw_temp)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def sign(record: Path, key: Path, output: Path) -> None:
    outside_repo(key, "private key")
    outside_repo(output, "signature")
    if output.exists() or output.is_symlink():
        raise SignatureError("signature output already exists")
    safe_file(key, "private key")
    result = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", NAMESPACE],
        input=record_bytes(record), capture_output=True, check=False,
    )
    if result.returncode or not result.stdout.startswith(b"-----BEGIN SSH SIGNATURE-----"):
        raise SignatureError("ssh-keygen could not sign the accepted record")
    atomic_write(output, result.stdout)


def verify(record: Path, signature: Path, allowed_signers: Path, identity: str) -> None:
    if not identity or "\n" in identity or "\r" in identity:
        raise SignatureError("signer identity is invalid")
    safe_file(signature, "signature")
    safe_file(allowed_signers, "allowed signers")
    result = subprocess.run(
        ["ssh-keygen", "-Y", "verify", "-f", str(allowed_signers),
         "-I", identity, "-n", NAMESPACE, "-s", str(signature)],
        input=record_bytes(record), capture_output=True, check=False,
    )
    if result.returncode:
        raise SignatureError("record signature verification failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    signer = modes.add_parser("sign")
    signer.add_argument("--record", type=Path, required=True)
    signer.add_argument("--key", type=Path, required=True)
    signer.add_argument("--output", type=Path, required=True)
    verifier = modes.add_parser("verify")
    verifier.add_argument("--record", type=Path, required=True)
    verifier.add_argument("--signature", type=Path, required=True)
    verifier.add_argument("--allowed-signers", type=Path, required=True)
    verifier.add_argument("--identity", required=True)
    args = parser.parse_args()
    if args.mode == "sign":
        sign(args.record, args.key, args.output)
        print("SIGNATURE_CREATED")
    else:
        verify(args.record, args.signature, args.allowed_signers, args.identity)
        print("SIGNATURE_VERIFIED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, SignatureError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
