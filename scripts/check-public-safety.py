#!/usr/bin/env python3
"""Reject files that should never be published in the public blueprint."""

from __future__ import annotations

import ipaddress
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TRACKED_PATHS = {
    "ansible/inventory/production/hosts.yml",
}
FORBIDDEN_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".kdbx"}
FORBIDDEN_NAMES = {".env", "id_rsa", "id_ed25519"}
# Build key markers at runtime so the safety scanner does not contain literal
# secret-detector signatures that would correctly trigger Gitleaks on itself.
PRIVATE_KEY_MARKERS = tuple(
    "-----BEGIN " + label + "-----"
    for label in ("PRIVATE KEY", "RSA PRIVATE KEY", "OPENSSH PRIVATE KEY")
)
IPV4 = re.compile(r"(?<![0-9.])(?:\d{1,3}\.){3}\d{1,3}(?![0-9.])")
ALLOWED_PRIVATE_IPS = {"127.0.0.1"}


def files_to_scan() -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]

    return [ROOT / raw.decode() for raw in output.split(b"\0") if raw]


def main() -> int:
    failures: list[str] = []

    for path in files_to_scan():
        relative = path.relative_to(ROOT).as_posix()
        if relative == "scripts/check-public-safety.py":
            continue

        if relative in FORBIDDEN_TRACKED_PATHS:
            failures.append(f"forbidden tracked Production file: {relative}")
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"sensitive file type/name is tracked: {relative}")

        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        if any(marker in text for marker in PRIVATE_KEY_MARKERS):
            failures.append(f"private-key material found: {relative}")

        if ".home.arpa" in text.lower():
            failures.append(f"private home.arpa name found: {relative}")

        for candidate in IPV4.findall(text):
            try:
                address = ipaddress.ip_address(candidate)
            except ValueError:
                continue
            if (
                address.version == 4
                and address.is_private
                and candidate not in ALLOWED_PRIVATE_IPS
            ):
                failures.append(f"private IPv4 address {candidate} found: {relative}")

    if failures:
        for failure in sorted(set(failures)):
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("Public-safety validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
