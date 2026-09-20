#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys

IMAGE = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
CLEAN_ENV = {
    "HOME": "/root",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
}


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        text=True,
        capture_output=True,
        env=CLEAN_ENV,
    )


def decode_images(encoded: str) -> list[str]:
    try:
        raw = base64.b64decode(encoded, validate=True)
        value = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid base64 JSON image list") from exc
    if not isinstance(value, list) or not value:
        raise ValueError("image list must be a non-empty JSON array")
    images: list[str] = []
    for item in value:
        if not isinstance(item, str) or not IMAGE.fullmatch(item):
            raise ValueError(f"image is not immutable by digest: {item!r}")
        if item not in images:
            images.append(item)
    return images


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images-b64", required=True)
    parser.add_argument("--scope", choices=("candidate", "rollback"), required=True)
    parser.add_argument("--docker-path", default="/usr/bin/docker")
    args = parser.parse_args()

    try:
        images = decode_images(args.images_b64)
    except ValueError as exc:
        print(f"ERROR: {args.scope} image preflight: {exc}", file=sys.stderr)
        return 2

    for image in images:
        inspect = run([args.docker_path, "image", "inspect", image])
        if inspect.returncode == 0:
            print(f"AVAILABLE {args.scope} {image}")
            continue

        pull = run([args.docker_path, "pull", image])
        if pull.returncode != 0:
            detail = pull.stderr.strip() or pull.stdout.strip() or "docker pull failed"
            print(
                f"ERROR: {args.scope} image unavailable by digest: {image}: {detail}",
                file=sys.stderr,
            )
            return 1

        verify = run([args.docker_path, "image", "inspect", image])
        if verify.returncode != 0:
            detail = verify.stderr.strip() or verify.stdout.strip() or "docker image inspect failed"
            print(
                f"ERROR: {args.scope} image was pulled but is not inspectable by digest: "
                f"{image}: {detail}",
                file=sys.stderr,
            )
            return 1

        print(f"PREFETCHED {args.scope} {image}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
