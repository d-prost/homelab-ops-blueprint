#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

for command_name in ansible ssh-keygen sshd; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    if [[ "${HOMELAB_STRICT_VALIDATION:-0}" == "1" ]]; then
      printf 'ERROR: %s is required for strict SSH host-key proof.\n' "$command_name" >&2
      exit 1
    fi
    printf 'SSH host-key proof skipped: %s unavailable.\n' "$command_name"
    exit 0
  fi
done

tmp_root="$(mktemp -d)"
sshd_pid=""
cleanup() {
  if [[ -n "$sshd_pid" ]]; then
    sudo kill "$sshd_pid" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$tmp_root"
}
trap cleanup EXIT

ssh-keygen -q -t ed25519 -N '' -f "$tmp_root/host-a"
ssh-keygen -q -t ed25519 -N '' -f "$tmp_root/host-b"
port="$(python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
)"

cat >"$tmp_root/sshd_config" <<EOF
Port $port
ListenAddress 127.0.0.1
HostKey $tmp_root/host-a
PidFile $tmp_root/sshd.pid
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication no
UsePAM no
PermitRootLogin no
StrictModes no
LogLevel ERROR
EOF

sudo install -d -m 0755 /run/sshd
sudo /usr/sbin/sshd -D -f "$tmp_root/sshd_config" -E "$tmp_root/sshd.log" &
sshd_pid=$!

for _ in $(seq 1 50); do
  if (echo >/dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done
kill -0 "$sshd_pid" >/dev/null 2>&1 || {
  cat "$tmp_root/sshd.log" >&2 || true
  exit 1
}

run_ansible_refusal() {
  local known_hosts="$1"
  local logfile="$2"
  cat >"$tmp_root/hosts.yml" <<EOF
---
all:
  hosts:
    ssh-target:
      ansible_connection: ssh
      ansible_host: 127.0.0.1
      ansible_port: $port
      ansible_user: nobody
      ansible_ssh_common_args: "-o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$known_hosts"
EOF
  set +e
  ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"   ANSIBLE_HOST_KEY_CHECKING=True     timeout 10 ansible all -i "$tmp_root/hosts.yml" -m ansible.builtin.ping >"$logfile" 2>&1
  local rc=$?
  set -e
  ((rc != 0)) || { cat "$logfile" >&2; return 1; }
  grep -Eiq 'host key verification failed|remote host identification has changed|no .* host key is known' "$logfile" || {
    cat "$logfile" >&2
    return 1
  }
}

: >"$tmp_root/known_hosts.empty"
run_ansible_refusal "$tmp_root/known_hosts.empty" "$tmp_root/unknown.log"

{
  printf '[127.0.0.1]:%s ' "$port"
  cat "$tmp_root/host-b.pub"
} >"$tmp_root/known_hosts.mismatch"
run_ansible_refusal "$tmp_root/known_hosts.mismatch" "$tmp_root/mismatch.log"

printf 'SSH host-key proof passed: unknown and replaced host identities are refused by Ansible/OpenSSH.\n'
