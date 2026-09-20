#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${HOMELAB_LAB_ACCEPTANCE_FAILURE_TEST:-0}" == "1" ]] || {
  printf 'ERROR: set HOMELAB_LAB_ACCEPTANCE_FAILURE_TEST=1.\n' >&2
  exit 1
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

export HOMELAB_LAB_HOSTNAME
HOMELAB_LAB_HOSTNAME="$(/bin/hostname)"

target_dir="/opt/homelab-ops/stacks/dozzle"
record_file="/etc/homelab-ops/deployments/dozzle.record"
marker_file="/var/lib/homelab-ops/transactions/dozzle.unresolved"
tmp_root="$(mktemp -d)"
baseline_log="$tmp_root/baseline.log"
failure_log="$tmp_root/failure.log"
blocked_log="$tmp_root/blocked.log"

cleanup() {
  set +e
  if [[ -f "$target_dir/docker-compose.yml" && -f "$target_dir/defaults.env" ]]; then
    sudo /usr/bin/docker compose       --env-file "$target_dir/defaults.env"       -f "$target_dir/docker-compose.yml"       down --remove-orphans >/dev/null 2>&1
  fi
  sudo rm -rf -- "$target_dir"
  sudo rm -f -- "$record_file" "$marker_file"
  rm -rf -- "$tmp_root"
}
trap cleanup EXIT

[[ ! -e "$target_dir" ]] || {
  printf 'ERROR: disposable Lab target already exists: %s\n' "$target_dir" >&2
  exit 1
}

bash scripts/deploy-stack.sh dozzle --inventory lab >"$baseline_log" 2>&1

baseline_record_hash="$(sudo sha256sum "$record_file" | awk '{print $1}')"
baseline_transaction_id="$(
  sudo sed -nE 's/^transaction_id=(.+)$/\1/p' "$record_file"
)"
[[ -n "$baseline_transaction_id" ]] || {
  printf 'FAIL: baseline acceptance record has no transaction_id.\n' >&2
  exit 1
}
[[ ! -e "$marker_file" ]] || {
  printf 'FAIL: successful baseline deployment left an unresolved marker.\n' >&2
  exit 1
}

set +e
HOMELAB_LAB_ACCEPTANCE_FAILURE_TEST=1   bash scripts/deploy-stack.sh dozzle --inventory lab >"$failure_log" 2>&1
failure_rc=$?
set -e
((failure_rc != 0)) || {
  printf 'FAIL: injected acceptance persistence failure unexpectedly succeeded.\n' >&2
  exit 1
}

grep -Fq 'Run functional stack verification on the target' "$failure_log" || {
  printf 'FAIL: persistence failure was not injected after functional verification.\n' >&2
  cat "$failure_log" >&2
  exit 1
}
grep -Fq 'ACCEPTANCE_PERSISTENCE_FAILED' "$failure_log" || {
  printf 'FAIL: terminal acceptance persistence failure was not reported.\n' >&2
  cat "$failure_log" >&2
  exit 1
}
if grep -Fq 'Restore prior managed files' "$failure_log"; then
  printf 'FAIL: acceptance persistence failure incorrectly entered automatic rollback.\n' >&2
  cat "$failure_log" >&2
  exit 1
fi

post_failure_record_hash="$(sudo sha256sum "$record_file" | awk '{print $1}')"
post_failure_transaction_id="$(
  sudo sed -nE 's/^transaction_id=(.+)$/\1/p' "$record_file"
)"
[[ "$post_failure_record_hash" == "$baseline_record_hash" ]] || {
  printf 'FAIL: failed acceptance persistence modified the last durable record.\n' >&2
  exit 1
}
[[ "$post_failure_transaction_id" == "$baseline_transaction_id" ]] || {
  printf 'FAIL: failed transaction replaced the previous accepted transaction ID.\n' >&2
  exit 1
}

sudo test -f "$marker_file" || {
  printf 'FAIL: acceptance persistence failure did not leave an unresolved marker.\n' >&2
  exit 1
}
failed_transaction_id="$(
  sudo sed -nE 's/^transaction_id=(.+)$/\1/p' "$marker_file"
)"
[[ -n "$failed_transaction_id" && "$failed_transaction_id" != "$baseline_transaction_id" ]] || {
  printf 'FAIL: unresolved marker does not identify the failed transaction.\n' >&2
  exit 1
}
sudo grep -Fxq 'mutation_started=true' "$marker_file" || {
  printf 'FAIL: unresolved marker does not record mutation boundary crossing.\n' >&2
  exit 1
}

sudo /usr/bin/python3 "$repo_root/scripts/verify-compose-health.py"   --stack-dir "$target_dir"   --compose-file docker-compose.yml   --env-file defaults.env   --contract "$repo_root/stacks/dozzle/stack.yml"

set +e
bash scripts/deploy-stack.sh dozzle --inventory lab >"$blocked_log" 2>&1
blocked_rc=$?
set -e
((blocked_rc != 0)) || {
  printf 'FAIL: unresolved acceptance state did not block a new transaction.\n' >&2
  exit 1
}
grep -Fq 'PRE_MUTATION_REFUSAL: unresolved transaction state exists' "$blocked_log" || {
  printf 'FAIL: blocked follow-up transaction did not report unresolved state.\n' >&2
  cat "$blocked_log" >&2
  exit 1
}

printf 'Acceptance persistence proof passed: runtime PASS + record failure stayed unaccepted, skipped rollback, preserved the previous record and blocked the next transaction.\n'
