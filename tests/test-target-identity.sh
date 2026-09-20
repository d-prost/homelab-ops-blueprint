#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
command -v ansible-playbook >/dev/null 2>&1 || {
  if [[ "${HOMELAB_STRICT_VALIDATION:-0}" == "1" ]]; then
    printf 'ERROR: ansible-playbook is required for strict target identity proof.\n' >&2
    exit 1
  fi
  printf 'Target identity runtime proof skipped: ansible-playbook unavailable.\n'
  exit 0
}

tmp_root="$(mktemp -d)"
cleanup() { rm -rf -- "$tmp_root"; }
trap cleanup EXIT

actual_hostname="$(/bin/hostname)"
actual_machine_id="$(cat /etc/machine-id)"
wrong_machine_id="00000000000000000000000000000000"
if [[ "$wrong_machine_id" == "$actual_machine_id" ]]; then
  wrong_machine_id="11111111111111111111111111111111"
fi

cat >"$tmp_root/playbook.yml" <<EOF
---
- name: Verify target identity fixture
  hosts: all
  gather_facts: false
  tasks:
    - name: Run repository identity contract
      ansible.builtin.include_tasks:
        file: "$repo_root/ansible/tasks/verify-target-identity.yml"
EOF

run_case() {
  local expected_hostname="$1"
  local machine_line="$2"
  local logfile="$3"
  cat >"$tmp_root/hosts.yml" <<EOF
---
all:
  hosts:
    fixture:
      ansible_connection: local
      homelab_environment: lab
      homelab_expected_hostname: "$expected_hostname"
$machine_line
EOF
  ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"     ansible-playbook -i "$tmp_root/hosts.yml" "$tmp_root/playbook.yml" >"$logfile" 2>&1
}

run_case "$actual_hostname" "" "$tmp_root/no-machine.log"

set +e
run_case "definitely-wrong-hostname.invalid" "" "$tmp_root/wrong-host.log"
wrong_host_rc=$?
set -e
((wrong_host_rc != 0)) || { cat "$tmp_root/wrong-host.log" >&2; exit 1; }
grep -Fq 'PRE_MUTATION_REFUSAL' "$tmp_root/wrong-host.log" || {
  cat "$tmp_root/wrong-host.log" >&2
  exit 1
}

run_case "$actual_hostname" "      homelab_expected_machine_id: \"$actual_machine_id\"" "$tmp_root/right-machine.log"

set +e
run_case "$actual_hostname" "      homelab_expected_machine_id: \"$wrong_machine_id\"" "$tmp_root/wrong-machine.log"
wrong_machine_rc=$?
set -e
((wrong_machine_rc != 0)) || { cat "$tmp_root/wrong-machine.log" >&2; exit 1; }
grep -Fq 'PRE_MUTATION_REFUSAL' "$tmp_root/wrong-machine.log" || {
  cat "$tmp_root/wrong-machine.log" >&2
  exit 1
}

printf 'Target identity runtime tests passed: hostname required, machine ID optional, mismatches refused before mutation.\n'
