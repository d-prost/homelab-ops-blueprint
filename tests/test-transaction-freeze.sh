#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_root="$(mktemp -d)"
cleanup(){ rm -rf -- "$tmp_root"; }
trap cleanup EXIT

fixture="$tmp_root/repo"
mkdir -p "$fixture/stacks/demo"
git -C "$fixture" init -q
git -C "$fixture" config user.name test
git -C "$fixture" config user.email test@example.invalid
printf 'version=one\n' >"$fixture/stacks/demo/payload.txt"
printf 'contract-one\n' >"$fixture/stacks/demo/stack.yml"
git -C "$fixture" add .
git -C "$fixture" commit -qm one
first_commit="$(git -C "$fixture" rev-parse HEAD)"

snapshot="$tmp_root/snapshot"
bash "$repo_root/scripts/materialize-git-snapshot.sh" \
  "$fixture" "$first_commit" "$snapshot" stacks/demo >/dev/null
first_snapshot_hash="$(sha256sum "$snapshot/stacks/demo/payload.txt" | awk '{print $1}')"

printf 'version=two\n' >"$fixture/stacks/demo/payload.txt"
printf 'contract-two\n' >"$fixture/stacks/demo/stack.yml"
git -C "$fixture" add .
git -C "$fixture" commit -qm two
second_commit="$(git -C "$fixture" rev-parse HEAD)"
[[ "$first_commit" != "$second_commit" ]]

second_snapshot_hash="$(sha256sum "$snapshot/stacks/demo/payload.txt" | awk '{print $1}')"
[[ "$first_snapshot_hash" == "$second_snapshot_hash" ]] || {
  printf 'FAIL: frozen snapshot changed after Git ref moved.\n' >&2
  exit 1
}
grep -Fxq 'version=one' "$snapshot/stacks/demo/payload.txt" || {
  printf 'FAIL: frozen candidate no longer contains the first commit payload.\n' >&2
  exit 1
}

if bash "$repo_root/scripts/materialize-git-snapshot.sh" \
  "$fixture" "$second_commit" "$tmp_root/unsafe" ../escape >/dev/null 2>&1; then
  printf 'FAIL: snapshot helper accepted an unsafe path.\n' >&2
  exit 1
fi

printf 'Transaction freeze proof passed.\n'
