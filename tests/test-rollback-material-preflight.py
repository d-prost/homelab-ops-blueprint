#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-stack-contracts.py"
MATERIALIZE = ROOT / "scripts" / "materialize-git-snapshot.sh"
PROVE_IMAGES = ROOT / "scripts" / "prove-image-availability.py"
RENDER_IMAGES = ROOT / "scripts" / "render-stack-images.py"
VALID_IMAGE = "example.invalid/demo@sha256:" + "a" * 64


def run(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True)


def require_failure(result: subprocess.CompletedProcess[str], expected: str) -> None:
    if result.returncode == 0:
        raise AssertionError(f"expected failure: {result.args}")
    combined = result.stdout + result.stderr
    if expected not in combined:
        raise AssertionError(f"missing failure text {expected!r}:\n{combined}")


def encode_images(images: list[str]) -> str:
    raw = json.dumps(images, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)

    stack = tmpdir / "dozzle"
    shutil.copytree(ROOT / "stacks" / "dozzle", stack)

    ok = run("python3", str(VALIDATOR), "--stack-dir", str(stack))
    if ok.returncode:
        raise AssertionError(ok.stdout + ok.stderr)

    bad_manifest = stack / "MANIFEST.tsv"
    original_manifest = bad_manifest.read_text(encoding="utf-8")
    bad_manifest.write_text(
        original_manifest.replace("defaults.env", "missing.env"),
        encoding="utf-8",
    )
    require_failure(
        run("python3", str(VALIDATOR), "--stack-dir", str(stack)),
        "MANIFEST.tsv differs from stack.yml",
    )
    bad_manifest.write_text(original_manifest, encoding="utf-8")

    (stack / "defaults.env").unlink()
    require_failure(
        run("python3", str(VALIDATOR), "--stack-dir", str(stack)),
        "managed source is missing: defaults.env",
    )

    missing_commit = "0" * 40
    require_failure(
        run(
            "bash",
            str(MATERIALIZE),
            str(ROOT),
            missing_commit,
            str(tmpdir / "missing-snapshot"),
            "stacks/dozzle",
        ),
        "",
    )

    fake_render = tmpdir / "fake-render-docker"
    fake_render.write_text(
        "#!/bin/sh\nprintf '%s\\n' '" + VALID_IMAGE + "'\n",
        encoding="utf-8",
    )
    fake_render.chmod(0o755)
    rendered = run(
        "python3",
        str(RENDER_IMAGES),
        "--stack-dir",
        str(ROOT / "stacks" / "dozzle"),
        "--docker-path",
        str(fake_render),
        "--base64-json",
    )
    if rendered.returncode:
        raise AssertionError(rendered.stdout + rendered.stderr)
    decoded = json.loads(base64.b64decode(rendered.stdout.strip()).decode("utf-8"))
    if decoded != [VALID_IMAGE]:
        raise AssertionError(f"unexpected rendered images: {decoded!r}")

    fake_success = tmpdir / "fake-docker-success"
    fake_success.write_text(
        """#!/bin/sh
state="$0.pulled"
if [ "$1" = "image" ] && [ "$2" = "inspect" ]; then
  [ -f "$state" ]
  exit $?
fi
if [ "$1" = "pull" ]; then
  : >"$state"
  exit 0
fi
exit 2
""",
        encoding="utf-8",
    )
    fake_success.chmod(0o755)

    available = run(
        "python3",
        str(PROVE_IMAGES),
        "--scope",
        "candidate",
        "--images-b64",
        encode_images([VALID_IMAGE]),
        "--docker-path",
        str(fake_success),
    )
    if available.returncode or "PREFETCHED candidate" not in available.stdout:
        raise AssertionError(available.stdout + available.stderr)

    fake_failure = tmpdir / "fake-docker-failure"
    fake_failure.write_text(
        """#!/bin/sh
if [ "$1" = "image" ] && [ "$2" = "inspect" ]; then
  exit 1
fi
if [ "$1" = "pull" ]; then
  echo 'registry unavailable' >&2
  exit 1
fi
exit 2
""",
        encoding="utf-8",
    )
    fake_failure.chmod(0o755)

    for scope in ("candidate", "rollback"):
        result = run(
            "python3",
            str(PROVE_IMAGES),
            "--scope",
            scope,
            "--images-b64",
            encode_images([VALID_IMAGE]),
            "--docker-path",
            str(fake_failure),
        )
        require_failure(result, f"ERROR: {scope} image unavailable by digest")

print(
    "Rollback-material preflight tests passed: prior Git material, manifest/payload "
    "integrity, canonical image rendering and candidate/rollback digest availability."
)
