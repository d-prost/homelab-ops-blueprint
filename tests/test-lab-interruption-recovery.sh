#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${HOMELAB_LAB_INTERRUPTION_TEST:-0}" == "1" ]] || {
  printf 'ERROR: set HOMELAB_LAB_INTERRUPTION_TEST=1.\n' >&2
  exit 1
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

export HOMELAB_LAB_HOSTNAME
HOMELAB_LAB_HOSTNAME="$(/bin/hostname)"
export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"

target_dir="/opt/homelab-ops/stacks/dozzle"
record_file="/etc/homelab-ops/deployments/dozzle.record"
receipt_file="/etc/homelab-ops/deployments/dozzle.receipt"
marker_file="/var/lib/homelab-ops/transactions/dozzle.unresolved"
tmp_root="$(mktemp -d)"
prepared_tx="prepared-interruption-test"
interrupted_tx="mutation-interruption-test"
prepared_candidate_dir="/var/lib/homelab-ops/candidates/dozzle-$prepared_tx"
interrupted_candidate_dir="/var/lib/homelab-ops/candidates/dozzle-$interrupted_tx"
interrupted_rollback_dir="/var/lib/homelab-ops/candidates/dozzle-$interrupted_tx-rollback"
mutation_pid=""
restore_pid=""

kill_group() {
  local pid="$1"
  [[ -n "$pid" ]] || return 0
  sudo kill -KILL -- "-$pid" >/dev/null 2>&1 || true
  wait "$pid" >/dev/null 2>&1 || true
}

cleanup() {
  set +e
  kill_group "$mutation_pid"
  kill_group "$restore_pid"
  if [[ -f "$target_dir/docker-compose.yml" && -f "$target_dir/defaults.env" ]]; then
    sudo /usr/bin/docker compose \
      --env-file "$target_dir/defaults.env" \
      -f "$target_dir/docker-compose.yml" \
      down --remove-orphans >/dev/null 2>&1
  fi
  sudo rm -rf -- "$target_dir"
  sudo rm -f -- "$record_file" "$receipt_file" "$marker_file"
  sudo rm -rf -- \
    "$prepared_candidate_dir" \
    "$interrupted_candidate_dir" \
    "$interrupted_rollback_dir"
  rm -rf -- "$tmp_root"
}
trap cleanup EXIT

[[ ! -e "$target_dir" ]] || {
  printf 'ERROR: disposable Lab target already exists: %s\n' "$target_dir" >&2
  exit 1
}

wait_for() {
  local description="$1"
  local pid="$2"
  shift 2
  for _ in $(seq 1 300); do
    if "$@"; then
      return 0
    fi
    if [[ -n "$pid" ]] && ! kill -0 "$pid" >/dev/null 2>&1; then
      printf 'FAIL: process exited while waiting for %s.\n' "$description" >&2
      return 1
    fi
    sleep 0.1
  done
  printf 'FAIL: timed out waiting for %s.\n' "$description" >&2
  return 1
}

marker_has_phase() {
  sudo grep -Fxq "phase=$1" "$marker_file" 2>/dev/null
}

# Prove an interruption that never crossed managed mutation is cleanup-only.
sudo install -d -m 0750 /var/lib/homelab-ops/transactions
sudo install -d -m 0700 "$prepared_candidate_dir"
printf 'transient\n' | sudo tee "$prepared_candidate_dir/transient.txt" >/dev/null
cat >"$tmp_root/prepared.marker" <<EOF
transaction_id=$prepared_tx
stack=dozzle
candidate_commit=1111111111111111111111111111111111111111
previous_accepted_commit=
previous_record_id=
phase=PREPARED
EOF
sudo /usr/bin/python3 "$repo_root/scripts/durable-state-file.py" commit \
  --source "$tmp_root/prepared.marker" \
  --destination "$marker_file" \
  --mode 0600

bash scripts/deploy-stack.sh dozzle --inventory lab >"$tmp_root/baseline.log" 2>&1
grep -Fq 'interrupted PREPARED transaction' "$tmp_root/baseline.log" || {
  printf 'FAIL: PREPARED interruption was not resolved as cleanup-only.\n' >&2
  cat "$tmp_root/baseline.log" >&2
  exit 1
}
[[ ! -e "$prepared_candidate_dir" && ! -e "$marker_file" ]] || {
  printf 'FAIL: PREPARED cleanup left target transaction artifacts.\n' >&2
  exit 1
}

baseline_compose_hash="$(sudo sha256sum "$target_dir/docker-compose.yml" | awk '{print $1}')"
sudo cat "$record_file" >"$tmp_root/previous.record"
previous_record_id="$(sha256sum "$tmp_root/previous.record" | awk '{print $1}')"
previous_commit="$(
  sed -nE 's/^commit=([0-9a-f]{40})$/\1/p' "$tmp_root/previous.record"
)"
[[ "$previous_commit" =~ ^[0-9a-f]{40}$ ]] || {
  printf 'FAIL: baseline record does not contain an accepted commit.\n' >&2
  exit 1
}

release_root="$tmp_root/release"
mkdir -p "$release_root/stacks"
cp -a "$repo_root/stacks/dozzle" "$release_root/stacks/dozzle"
printf '\n# interrupted-candidate-marker\n' >>"$release_root/stacks/dozzle/compose.yaml"
contract_hash="$(sha256sum "$release_root/stacks/dozzle/stack.yml" | awk '{print $1}')"
manifest_hash="$(sha256sum "$release_root/stacks/dozzle/MANIFEST.tsv" | awk '{print $1}')"
tooling_commit="$(git rev-parse HEAD)"

setsid env HOMELAB_LAB_INTERRUPT_TEST=mutation \
  HOMELAB_LAB_HOSTNAME="$HOMELAB_LAB_HOSTNAME" \
  ANSIBLE_CONFIG="$ANSIBLE_CONFIG" \
  ansible-playbook \
    -i "$repo_root/ansible/inventory/lab/hosts.yml" \
    "$repo_root/ansible/playbooks/deploy-stack.yml" \
    -e "stack_name=dozzle" \
    -e "homelab_release_commit=1111111111111111111111111111111111111111" \
    -e "homelab_tooling_commit=$tooling_commit" \
    -e "homelab_transaction_id=$interrupted_tx" \
    -e "homelab_contract_hash=$contract_hash" \
    -e "homelab_manifest_hash=$manifest_hash" \
    -e "homelab_previous_accepted_commit=$previous_commit" \
    -e "homelab_previous_record_id=$previous_record_id" \
    -e "homelab_previous_record_source=$tmp_root/previous.record" \
    -e "homelab_previous_release_root=$repo_root" \
    -e "homelab_repo_root=$repo_root" \
    -e "homelab_release_root=$release_root" \
    >"$tmp_root/mutation.log" 2>&1 &
mutation_pid=$!

wait_for "post-mutation pause" "$mutation_pid" bash -c \
  "sudo grep -Fxq 'phase=MUTATING' '$marker_file' 2>/dev/null && sudo grep -Fq '# interrupted-candidate-marker' '$target_dir/docker-compose.yml' 2>/dev/null"

sudo test -f "$interrupted_rollback_dir/previous.record" || {
  printf 'FAIL: interruption rollback snapshot lacks previous accepted record.\n' >&2
  exit 1
}
sudo test -f "$interrupted_candidate_dir/stack.yml" || {
  printf 'FAIL: interruption candidate snapshot lacks its contract.\n' >&2
  exit 1
}

kill_group "$mutation_pid"
mutation_pid=""

marker_has_phase MUTATING || {
  printf 'FAIL: forced mutation interruption did not leave MUTATING state.\n' >&2
  exit 1
}
mutated_hash="$(sudo sha256sum "$target_dir/docker-compose.yml" | awk '{print $1}')"
[[ "$mutated_hash" != "$baseline_compose_hash" ]] || {
  printf 'FAIL: forced interruption did not occur after managed configuration mutation.\n' >&2
  exit 1
}

# Kill the first reconciliation after it has entered RESTORING and copied back
# the prior files. The next invocation must retry recovery, not start a candidate.
setsid env HOMELAB_LAB_INTERRUPT_TEST=restore \
  HOMELAB_LAB_HOSTNAME="$HOMELAB_LAB_HOSTNAME" \
  bash scripts/deploy-stack.sh dozzle --inventory lab \
    >"$tmp_root/restore-interrupted.log" 2>&1 &
restore_pid=$!

restore_point_reached() {
  marker_has_phase RESTORING || return 1
  local current_hash
  current_hash="$(sudo sha256sum "$target_dir/docker-compose.yml" 2>/dev/null | awk '{print $1}')" || return 1
  [[ "$current_hash" == "$baseline_compose_hash" ]]
}

wait_for "restore interruption point" "$restore_pid" restore_point_reached

kill_group "$restore_pid"
restore_pid=""

marker_has_phase RESTORING || {
  printf 'FAIL: interrupted reconciliation did not leave RESTORING state.\n' >&2
  exit 1
}

bash scripts/deploy-stack.sh dozzle --inventory lab >"$tmp_root/final.log" 2>&1

grep -Fq 'REJECTED_ROLLBACK_VERIFIED' "$tmp_root/final.log" || {
  printf 'FAIL: retry did not report verified interruption rollback.\n' >&2
  cat "$tmp_root/final.log" >&2
  exit 1
}
[[ ! -e "$marker_file" ]] || {
  printf 'FAIL: successful recovery/new acceptance left an unresolved marker.\n' >&2
  exit 1
}
final_hash="$(sudo sha256sum "$target_dir/docker-compose.yml" | awk '{print $1}')"
[[ "$final_hash" == "$baseline_compose_hash" ]] || {
  printf 'FAIL: final managed configuration differs from the accepted baseline.\n' >&2
  exit 1
}

sudo /usr/bin/python3 "$repo_root/scripts/verify-compose-health.py" \
  --stack-dir "$target_dir" \
  --compose-file docker-compose.yml \
  --env-file defaults.env \
  --contract "$repo_root/stacks/dozzle/stack.yml"

printf 'Interruption recovery proof passed: PREPARED cleaned without rollback, MUTATING kill restored previous accepted state, interrupted RESTORING retried idempotently, and functional verification cleared unresolved state.\n'
