#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_root="$(mktemp -d)"
cleanup() { rm -rf -- "$tmp_root"; }
trap cleanup EXIT

fixture="$tmp_root/repo"
mkdir -p "$fixture"
tar -C "$repo_root" --exclude=.git -cf - . | tar -C "$fixture" -xf -
git -C "$fixture" init -q -b main
git -C "$fixture" config user.name failure-matrix
git -C "$fixture" config user.email failure-matrix@example.invalid
git -C "$fixture" add .
git -C "$fixture" commit -qm baseline
baseline="$(git -C "$fixture" rev-parse HEAD)"

export HOMELAB_LAB_HOSTNAME
HOMELAB_LAB_HOSTNAME="$(/bin/hostname)"

expect_refusal() {
  local name="$1"
  local expected_detail="$2"
  local log="$tmp_root/$name.log"

  set +e
  (
    cd "$fixture"
    bash scripts/deploy-stack.sh dozzle --inventory lab --check
  ) >"$log" 2>&1
  local rc=$?
  set -e

  ((rc != 0)) || {
    printf 'FAIL: %s unexpectedly succeeded.\n' "$name" >&2
    cat "$log" >&2
    exit 1
  }
  grep -Fq 'PRE_MUTATION_REFUSAL: candidate stack contract or manifest validation failed' "$log" || {
    printf 'FAIL: %s did not report PRE_MUTATION_REFUSAL.\n' "$name" >&2
    cat "$log" >&2
    exit 1
  }
  grep -Fq "$expected_detail" "$log" || {
    printf 'FAIL: %s did not expose the expected validator reason.\n' "$name" >&2
    cat "$log" >&2
    exit 1
  }
}

reset_fixture() {
  git -C "$fixture" reset -q --hard "$baseline"
  git -C "$fixture" clean -qfd
}

python3 - "$fixture/stacks/dozzle/stack.yml" <<'PY'
from pathlib import Path
import sys, yaml
p=Path(sys.argv[1]); model=yaml.safe_load(p.read_text())
model["stack_target_dir"]="/etc/not-allowed"
p.write_text(yaml.safe_dump(model,sort_keys=False))
PY
git -C "$fixture" add stacks/dozzle/stack.yml
git -C "$fixture" commit -qm invalid-contract
expect_refusal invalid-contract "unsafe target directory"
reset_fixture

printf 'compose.yaml\t/opt/homelab-ops/stacks/dozzle/wrong-name.yml\n' >"$fixture/stacks/dozzle/MANIFEST.tsv"
git -C "$fixture" add stacks/dozzle/MANIFEST.tsv
git -C "$fixture" commit -qm invalid-manifest
expect_refusal invalid-manifest "MANIFEST.tsv differs from stack.yml"
reset_fixture

python3 - "$fixture/stacks/dozzle/defaults.env" <<'PY'
from pathlib import Path
import re, sys
p=Path(sys.argv[1])
text=p.read_text()
text=re.sub(r'@sha256:[0-9a-f]{64}', ':latest', text)
p.write_text(text)
PY
git -C "$fixture" add stacks/dozzle/defaults.env
git -C "$fixture" commit -qm mutable-image
expect_refusal mutable-image "images must be pinned by digest"

printf 'Failure-matrix preflight proof passed: invalid contract, manifest and mutable image all return PRE_MUTATION_REFUSAL.\n'
