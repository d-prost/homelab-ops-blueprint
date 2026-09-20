#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${HOMELAB_LAB_IDEMPOTENCY_TEST:-0}" == "1" ]] || {
  printf 'ERROR: set HOMELAB_LAB_IDEMPOTENCY_TEST=1.\n' >&2
  exit 1
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

actual_hostname="$(/bin/hostname)"
export HOMELAB_LAB_HOSTNAME="$actual_hostname"

target_dir="/opt/homelab-ops/stacks/dozzle"
record_file="/etc/homelab-ops/deployments/dozzle.record"
tmp_root="$(mktemp -d)"
first_log="$tmp_root/first.log"
second_log="$tmp_root/second.log"

cleanup() {
  set +e
  if [[ -f "$target_dir/docker-compose.yml" && -f "$target_dir/defaults.env" ]]; then
    sudo /usr/bin/docker compose       --env-file "$target_dir/defaults.env"       -f "$target_dir/docker-compose.yml"       down --remove-orphans >/dev/null 2>&1
  fi
  sudo rm -rf -- "$target_dir"
  sudo rm -f -- "$record_file"
  rm -rf -- "$tmp_root"
}
trap cleanup EXIT

[[ ! -e "$target_dir" ]] || {
  printf 'ERROR: disposable Lab target already exists: %s\n' "$target_dir" >&2
  exit 1
}

bash scripts/deploy-stack.sh dozzle --inventory lab >"$first_log" 2>&1

managed_fingerprint() {
  sudo stat -c '%n|%i|%s|%Y|%Z'     "$target_dir/docker-compose.yml"     "$target_dir/defaults.env"
  sudo sha256sum     "$target_dir/docker-compose.yml"     "$target_dir/defaults.env"
}

first_fingerprint="$(managed_fingerprint)"
first_transaction_id="$(
  sudo sed -nE 's/^transaction_id=(.+)$/\1/p' "$record_file"
)"
[[ -n "$first_transaction_id" ]] || {
  printf 'FAIL: first acceptance record has no transaction_id.\n' >&2
  exit 1
}

bash scripts/deploy-stack.sh dozzle --inventory lab >"$second_log" 2>&1

second_fingerprint="$(managed_fingerprint)"
second_transaction_id="$(
  sudo sed -nE 's/^transaction_id=(.+)$/\1/p' "$record_file"
)"

[[ "$first_fingerprint" == "$second_fingerprint" ]] || {
  printf 'FAIL: redeploying the accepted candidate changed managed configuration files.\n' >&2
  diff -u <(printf '%s\n' "$first_fingerprint") <(printf '%s\n' "$second_fingerprint") >&2 || true
  exit 1
}

[[ -n "$second_transaction_id" && "$second_transaction_id" != "$first_transaction_id" ]] || {
  printf 'FAIL: second deployment did not execute as a new transaction.\n' >&2
  exit 1
}

grep -Fq 'Run functional stack verification on the target' "$second_log" || {
  printf 'FAIL: idempotent redeploy skipped functional runtime verification.\n' >&2
  cat "$second_log" >&2
  exit 1
}
sudo grep -Fxq 'verified=functional' "$record_file" || {
  printf 'FAIL: second transaction was not accepted after functional verification.\n' >&2
  exit 1
}

sudo /usr/bin/python3 "$repo_root/scripts/verify-compose-health.py"   --stack-dir "$target_dir"   --compose-file docker-compose.yml   --env-file defaults.env   --contract "$repo_root/stacks/dozzle/stack.yml"

printf 'Idempotency proof passed: same candidate caused zero managed-file changes and still ran functional verification.\n'
