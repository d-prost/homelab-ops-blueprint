#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${HOMELAB_SSH_INTERRUPTION_TEST:-0}" == "1" ]] || {
  printf 'ERROR: set HOMELAB_SSH_INTERRUPTION_TEST=1.\n' >&2
  exit 1
}

for command_name in ansible ansible-playbook setsid ssh-keygen sshd; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'ERROR: required command unavailable for SSH interruption proof: %s\n' "$command_name" >&2
    exit 1
  }
done

sudo -n true >/dev/null 2>&1 || {
  printf 'ERROR: SSH interruption proof requires non-interactive sudo.\n' >&2
  exit 1
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

actual_hostname="$(/bin/hostname)"
export HOMELAB_LAB_HOSTNAME="$actual_hostname"
target_dir="/opt/homelab-ops/stacks/dozzle"
record_file="/etc/homelab-ops/deployments/dozzle.record"
receipt_file="/etc/homelab-ops/deployments/dozzle.receipt"
marker_file="/var/lib/homelab-ops/transactions/dozzle.unresolved"
tmp_root="$(mktemp -d)"
interrupted_tx="ssh-session-interruption-test"
candidate_dir="/var/lib/homelab-ops/candidates/dozzle-$interrupted_tx"
rollback_dir="/var/lib/homelab-ops/candidates/dozzle-$interrupted_tx-rollback"
sshd_pid=""
play_pid=""

kill_play_group() {
  if [[ -n "$play_pid" ]]; then
    sudo kill -KILL -- "-$play_pid" >/dev/null 2>&1 || true
    wait "$play_pid" >/dev/null 2>&1 || true
    play_pid=""
  fi
}

stop_sshd() {
  local daemon_pid=""
  if [[ -f "$tmp_root/sshd.pid" ]]; then
    daemon_pid="$(cat "$tmp_root/sshd.pid")"
  elif [[ -n "$sshd_pid" ]]; then
    daemon_pid="$sshd_pid"
  fi
  if [[ -n "$daemon_pid" ]]; then
    sudo pkill -KILL -P "$daemon_pid" >/dev/null 2>&1 || true
    sudo kill -KILL "$daemon_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$sshd_pid" ]]; then
    wait "$sshd_pid" >/dev/null 2>&1 || true
    sshd_pid=""
  fi
  rm -f -- "$tmp_root/sshd.pid"
}

cleanup() {
  set +e
  kill_play_group
  stop_sshd
  if [[ -f "$target_dir/docker-compose.yml" && -f "$target_dir/defaults.env" ]]; then
    sudo /usr/bin/docker compose \
      --env-file "$target_dir/defaults.env" \
      -f "$target_dir/docker-compose.yml" \
      down --remove-orphans >/dev/null 2>&1
  fi
  sudo rm -rf -- "$target_dir" "$candidate_dir" "$rollback_dir"
  sudo rm -f -- "$record_file" "$receipt_file" "$marker_file"
  rm -rf -- "$tmp_root"
}
trap cleanup EXIT

[[ ! -e "$target_dir" ]] || {
  printf 'ERROR: disposable Lab target already exists: %s\n' "$target_dir" >&2
  exit 1
}

ssh-keygen -q -t ed25519 -N '' -f "$tmp_root/host-key"
ssh-keygen -q -t ed25519 -N '' -f "$tmp_root/client-key"
cp "$tmp_root/client-key.pub" "$tmp_root/authorized_keys"
chmod 0600 "$tmp_root/authorized_keys"

port="$(python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"
ssh_user="$(id -un)"
cat >"$tmp_root/sshd_config" <<EOF
Port $port
ListenAddress 127.0.0.1
HostKey $tmp_root/host-key
PidFile $tmp_root/sshd.pid
AuthorizedKeysFile $tmp_root/authorized_keys
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
UsePAM no
PermitRootLogin no
StrictModes no
AllowUsers $ssh_user
LogLevel ERROR
EOF

{
  printf '[127.0.0.1]:%s ' "$port"
  cat "$tmp_root/host-key.pub"
} >"$tmp_root/known_hosts"

cat >"$tmp_root/hosts.yml" <<EOF
---
all:
  hosts:
    ssh-target:
      ansible_connection: ssh
      ansible_host: 127.0.0.1
      ansible_port: $port
      ansible_user: $ssh_user
      ansible_ssh_private_key_file: $tmp_root/client-key
      ansible_ssh_common_args: >-
        -o BatchMode=yes
        -o StrictHostKeyChecking=yes
        -o UserKnownHostsFile=$tmp_root/known_hosts
        -o ControlMaster=no
        -o ControlPersist=no
        -o ConnectionAttempts=1
        -o ConnectTimeout=2
        -o ServerAliveInterval=1
        -o ServerAliveCountMax=1
      homelab_environment: lab
      homelab_expected_hostname: "$actual_hostname"
EOF

start_sshd() {
  sudo install -d -m 0755 /run/sshd
  sudo /usr/sbin/sshd -D -f "$tmp_root/sshd_config" -E "$tmp_root/sshd.log" &
  sshd_pid=$!
  for _ in $(seq 1 100); do
    if [[ -f "$tmp_root/sshd.pid" ]] &&
       (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.1
  done
  printf 'FAIL: ephemeral sshd did not become ready.\n' >&2
  cat "$tmp_root/sshd.log" >&2 || true
  return 1
}

start_sshd

ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg" \
ANSIBLE_HOST_KEY_CHECKING=True \
  ansible all -i "$tmp_root/hosts.yml" -m ansible.builtin.ping \
  >"$tmp_root/ping.log" 2>&1 || {
    cat "$tmp_root/ping.log" >&2
    exit 1
  }

# Establish the previous accepted state through the ordinary local Lab path.
bash scripts/deploy-stack.sh dozzle --inventory lab >"$tmp_root/baseline.log" 2>&1
baseline_hash="$(sudo sha256sum "$target_dir/docker-compose.yml" | awk '{print $1}')"
sudo cat "$record_file" >"$tmp_root/previous.record"
previous_record_id="$(sha256sum "$tmp_root/previous.record" | awk '{print $1}')"
previous_commit="$(
  sed -nE 's/^commit=([0-9a-f]{40})$/\1/p' "$tmp_root/previous.record"
)"

release_root="$tmp_root/release"
mkdir -p "$release_root/stacks"
cp -a "$repo_root/stacks/dozzle" "$release_root/stacks/dozzle"
printf '\n# ssh-interrupted-candidate\n' >>"$release_root/stacks/dozzle/compose.yaml"
contract_hash="$(sha256sum "$release_root/stacks/dozzle/stack.yml" | awk '{print $1}')"
manifest_hash="$(sha256sum "$release_root/stacks/dozzle/MANIFEST.tsv" | awk '{print $1}')"
tooling_commit="$(git rev-parse HEAD)"

setsid env HOMELAB_LAB_INTERRUPT_TEST=mutation \
  ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg" \
  ANSIBLE_HOST_KEY_CHECKING=True \
  ansible-playbook -i "$tmp_root/hosts.yml" \
    "$repo_root/ansible/playbooks/deploy-stack.yml" \
    -e "stack_name=dozzle" \
    -e "homelab_release_commit=4444444444444444444444444444444444444444" \
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
    >"$tmp_root/ssh-interrupted.log" 2>&1 &
play_pid=$!

for _ in $(seq 1 300); do
  if sudo grep -Fxq 'phase=MUTATING' "$marker_file" 2>/dev/null &&
     sudo grep -Fq '# ssh-interrupted-candidate' "$target_dir/docker-compose.yml" 2>/dev/null; then
    break
  fi
  kill -0 "$play_pid" >/dev/null 2>&1 || {
    printf 'FAIL: SSH deployment exited before the disconnect point.\n' >&2
    cat "$tmp_root/ssh-interrupted.log" >&2
    exit 1
  }
  sleep 0.1
done

sudo grep -Fxq 'phase=MUTATING' "$marker_file" || {
  printf 'FAIL: SSH interruption fixture did not reach MUTATING.\n' >&2
  exit 1
}

# Drop the real SSH transport while Ansible is blocked in a remote command.
stop_sshd

for _ in $(seq 1 150); do
  if ! kill -0 "$play_pid" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

set +e
wait "$play_pid"
play_rc=$?
set -e
play_pid=""
((play_rc != 0)) || {
  printf 'FAIL: SSH session loss did not fail the in-flight deployment.\n' >&2
  exit 1
}
grep -Eiq 'UNREACHABLE|connection.*(closed|reset|refused)|failed to connect|broken pipe' "$tmp_root/ssh-interrupted.log" || {
  printf 'FAIL: deployment failed, but not with observable SSH transport loss.\n' >&2
  cat "$tmp_root/ssh-interrupted.log" >&2
  exit 1
}
sudo grep -Fxq 'phase=MUTATING' "$marker_file" || {
  printf 'FAIL: SSH session loss did not preserve unresolved MUTATING state.\n' >&2
  exit 1
}

start_sshd

ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg" \
ANSIBLE_HOST_KEY_CHECKING=True \
  ansible-playbook -i "$tmp_root/hosts.yml" \
    "$repo_root/ansible/playbooks/reconcile-interrupted.yml" \
    -e "stack_name=dozzle" \
    -e "homelab_interrupted_transaction_id=$interrupted_tx" \
    -e "homelab_interrupted_candidate_commit=4444444444444444444444444444444444444444" \
    -e "homelab_interrupted_previous_commit=$previous_commit" \
    -e "homelab_interrupted_previous_record_id=$previous_record_id" \
    -e "homelab_repo_root=$repo_root" \
    >"$tmp_root/ssh-recovery.log" 2>&1 || {
      cat "$tmp_root/ssh-recovery.log" >&2
      exit 1
    }

grep -Fq 'REJECTED_ROLLBACK_VERIFIED' "$tmp_root/ssh-recovery.log" || {
  printf 'FAIL: SSH recovery did not report verified rollback.\n' >&2
  cat "$tmp_root/ssh-recovery.log" >&2
  exit 1
}
[[ ! -e "$marker_file" ]] || {
  printf 'FAIL: SSH recovery left unresolved marker.\n' >&2
  exit 1
}
restored_hash="$(sudo sha256sum "$target_dir/docker-compose.yml" | awk '{print $1}')"
[[ "$restored_hash" == "$baseline_hash" ]] || {
  printf 'FAIL: SSH recovery did not restore the accepted managed configuration.\n' >&2
  exit 1
}

sudo /usr/bin/python3 "$repo_root/scripts/verify-compose-health.py" \
  --stack-dir "$target_dir" \
  --compose-file docker-compose.yml \
  --env-file defaults.env \
  --contract "$repo_root/stacks/dozzle/stack.yml"

printf 'SSH session interruption proof passed: real OpenSSH transport loss after mutation left MUTATING state, and restored transport re-established and reverified the previous accepted configuration.\n'
