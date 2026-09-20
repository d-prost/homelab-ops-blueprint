#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path

IMAGE = re.compile(r"^.+@sha256:[0-9a-f]{64}$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack-dir", required=True, type=Path)
    parser.add_argument("--docker-path", default="docker")
    parser.add_argument("--base64-json", action="store_true")
    args = parser.parse_args()

    stack_dir = args.stack_dir.resolve()
    compose_file = stack_dir / "compose.yaml"
    env_file = stack_dir / "defaults.env"
    if not compose_file.is_file() or not env_file.is_file():
        raise SystemExit(f"ERROR: incomplete stack payload: {stack_dir}")

    try:
        result = subprocess.run(
            [
                args.docker_path,
                "compose",
                "--env-file",
                str(env_file),
                "-f",
                str(compose_file),
                "config",
                "--images",
            ],
            cwd=stack_dir,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: docker command not found: {args.docker_path}") from exc

    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise SystemExit(f"ERROR: docker compose image rendering failed: {detail}")

    images: list[str] = []
    for raw in result.stdout.splitlines():
        image = raw.strip()
        if not image:
            continue
        if image not in images:
            images.append(image)

    if not images:
        raise SystemExit("ERROR: stack rendered no runtime images")
    invalid = [image for image in images if not IMAGE.fullmatch(image)]
    if invalid:
        raise SystemExit(
            "ERROR: rendered runtime image is not digest-pinned: " + ", ".join(invalid)
        )

    payload = json.dumps(images, separators=(",", ":")).encode("utf-8")
    if args.base64_json:
        print(base64.b64encode(payload).decode("ascii"))
    else:
        print(payload.decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
