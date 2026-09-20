#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${HOMELAB_LAB_STALE_MARKER_PROOF:-0}" == "1" ]] || {
  printf 'ERROR: set HOMELAB_LAB_STALE_MARKER_PROOF=1.\n' >&2
  exit 1
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

export HOMELAB_LAB_HOSTNAME
HOMELAB_LAB_HOSTNAME="$(/bin/hostname)"

target_dir="/opt/homelab-ops/stacks/dozzle"
record_file="/etc/homelab-ops/deployments/dozzle.record"
receipt_file="/etc/homelab-ops/deployments/dozzle.receipt"
marker_file="/var/lib/homelab-ops/transactions/dozzle.unresolved"
tmp_root="$(mktemp -d)"

cleanup() {
  set +e
  if [[ -f "$target_dir/docker-compose.yml" && -f "$target_dir/defaults.env" ]]; then
    sudo /usr/bin/docker compose \
      --env-file "$target_dir/defaults.env" \
      -f "$target_dir/docker-compose.yml" \
      down --remove-orphans >/dev/null 2>&1
  fi
  sudo rm -rf -- "$target_dir"
  sudo rm -f -- "$record_file" "$receipt_file" "$marker_file"
  rm -rf -- "$tmp_root"
}
trap cleanup EXIT

[[ ! -e "$target_dir" ]] || {
  printf 'ERROR: disposable Lab target already exists: %s\n' "$target_dir" >&2
  exit 1
}

if ! HOMELAB_LAB_STALE_MARKER_TEST=1 \
  bash scripts/deploy-stack.sh dozzle --inventory lab >"$tmp_root/first.log" 2>&1; then
  printf 'FAIL: stale-marker fixture deployment failed.\n' >&2
  cat "$tmp_root/first.log" >&2
  exit 1
fi

sudo test -f "$marker_file" || {
  printf 'FAIL: accepted stale-marker fixture did not leave unresolved marker.\n' >&2
  exit 1
}
sudo grep -Fxq 'phase=ACCEPTANCE_PENDING' "$marker_file" || {
  printf 'FAIL: stale accepted marker is not in ACCEPTANCE_PENDING phase.\n' >&2
  exit 1
}
sudo test -f "$record_file" || {
  printf 'FAIL: accepted stale-marker fixture has no durable record.\n' >&2
  exit 1
}
sudo test -f "$receipt_file" || {
  printf 'FAIL: accepted stale-marker fixture has no durable receipt.\n' >&2
  exit 1
}

marker_tx="$(sudo sed -nE 's/^transaction_id=(.+)$/\1/p' "$marker_file")"
record_tx="$(sudo sed -nE 's/^transaction_id=(.+)$/\1/p' "$record_file")"
receipt_tx="$(sudo sed -nE 's/^transaction_id=(.+)$/\1/p' "$receipt_file")"
record_hash="$(sudo sha256sum "$record_file" | awk '{print $1}')"
receipt_hash="$(sudo sed -nE 's/^record_sha256=([0-9a-f]{64})$/\1/p' "$receipt_file")"

[[ -n "$marker_tx" && "$marker_tx" == "$record_tx" && "$record_tx" == "$receipt_tx" ]] || {
  printf 'FAIL: durable acceptance proof does not bind marker, record and receipt to one transaction.\n' >&2
  exit 1
}
[[ "$record_hash" == "$receipt_hash" ]] || {
  printf 'FAIL: durable acceptance receipt does not bind the accepted record hash.\n' >&2
  exit 1
}

if ! bash scripts/deploy-stack.sh dozzle --inventory lab >"$tmp_root/second.log" 2>&1; then
  printf 'FAIL: follow-up deployment failed while resolving stale accepted marker.\n' >&2
  cat "$tmp_root/second.log" >&2
  exit 1
fi

grep -Fq 'stale marker cleared without rollback' "$tmp_root/second.log" || {
  printf 'FAIL: follow-up transaction did not prove and clear stale accepted marker.\n' >&2
  cat "$tmp_root/second.log" >&2
  exit 1
}
if grep -Fq 'REJECTED_ROLLBACK_VERIFIED' "$tmp_root/second.log"; then
  printf 'FAIL: stale accepted marker incorrectly triggered rollback.\n' >&2
  cat "$tmp_root/second.log" >&2
  exit 1
fi
[[ ! -e "$marker_file" ]] || {
  printf 'FAIL: stale accepted marker remains after durable proof.\n' >&2
  exit 1
}

new_record_tx="$(sudo sed -nE 's/^transaction_id=(.+)$/\1/p' "$record_file")"
[[ -n "$new_record_tx" && "$new_record_tx" != "$record_tx" ]] || {
  printf 'FAIL: follow-up deployment did not continue as a new transaction.\n' >&2
  exit 1
}

sudo /usr/bin/python3 "$repo_root/scripts/verify-compose-health.py" \
  --stack-dir "$target_dir" \
  --compose-file docker-compose.yml \
  --env-file defaults.env \
  --contract "$repo_root/stacks/dozzle/stack.yml"

printf 'Stale accepted marker proof passed: matching durable record + receipt cleared the stale marker without rollback, then a new transaction verified normally.\n'
