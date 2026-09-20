#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

grep -q 'check_mode: false' "$repo_root/ansible/tasks/verify-target-identity.yml"
grep -q 'check_mode: false' "$repo_root/ansible/playbooks/preflight.yml"
grep -Eq '^host_key_checking[[:space:]]*=[[:space:]]*True[[:space:]]*$' "$repo_root/ansible/ansible.cfg"
grep -Eq '^roles_path[[:space:]]*=[[:space:]]*\./roles[[:space:]]*$' "$repo_root/ansible/ansible.cfg"
grep -q 'ANSIBLE_HOST_KEY_CHECKING=True' "$repo_root/scripts/deploy-stack.sh"
grep -q 'target-lock-key.py' "$repo_root/scripts/deploy-stack.sh"
grep -q '/run/lock/homelab-ops-' "$repo_root/scripts/deploy-stack.sh"
grep -q 'homelab_acquire_global_lock' "$repo_root/scripts/deploy-stack.sh"
grep -q 'flock -n' "$repo_root/scripts/lock-utils.sh"
if grep -q 'XDG_RUNTIME_DIR' "$repo_root/scripts/deploy-stack.sh"; then
  printf 'FAIL: deploy lock must not use a user-specific runtime directory.\n' >&2
  exit 1
fi
grep -q 'validate-target-inventory.py' "$repo_root/scripts/deploy-stack.sh"
grep -q 'verify-target-identity.yml' "$repo_root/ansible/playbooks/preflight.yml"
grep -q 'verify-target-identity.yml' "$repo_root/ansible/playbooks/deploy-stack.yml"
grep -q 'ansible_connection: ssh' "$repo_root/ansible/inventory/production/hosts.example.yml"
grep -q 'homelab_expected_machine_id: null' "$repo_root/ansible/inventory/production/hosts.example.yml"
grep -q 'target_hostname=' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'target_machine_id=' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'homelab_transaction_state_dir' "$repo_root/ansible/group_vars/all.yml"
grep -q 'unresolved transaction state exists' "$repo_root/ansible/playbooks/preflight.yml"
grep -q 'durable-state-file.py' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'Commit acceptance record atomically and durably' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'ACCEPTANCE_PERSISTENCE_FAILED' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'automatic rollback is intentionally not attempted' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
if grep -q 'VERIFIED_BUT_NOT_RECORDED' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"; then
  printf 'FAIL: acceptance persistence must not create a stable verified-but-unrecorded state.\n' >&2
  exit 1
fi

grep -q 'local main control plane is not exactly origin/main' "$repo_root/scripts/deploy-stack.sh"
grep -q 'prior managed files were restored' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'stack_functional_checks' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'delegate_to: localhost' "$repo_root/ansible/playbooks/preflight.yml"
grep -q 'ansible.builtin.script:' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'Load exact prior contract from frozen transaction snapshot' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
if grep -q '/usr/bin/git' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"; then
  printf 'FAIL: managed role must not consult Git after transaction preparation.\n' >&2
  exit 1
fi
grep -q 'read-accepted-record.yml' "$repo_root/scripts/deploy-stack.sh"
grep -q 'materialize-git-snapshot.sh' "$repo_root/scripts/deploy-stack.sh"
grep -q 'preflight-images.yml' "$repo_root/scripts/deploy-stack.sh"
grep -q 'prove-image-availability.py' "$repo_root/ansible/playbooks/preflight-images.yml"
grep -q 'validate-stack-contracts.py" --stack-dir' "$repo_root/scripts/deploy-stack.sh"
grep -q 'Historical refs provide' "$repo_root/scripts/deploy-stack.sh"
grep -q 'MANIFEST.tsv differs from stack.yml' "$repo_root/scripts/validate-stack-contracts.py"
printf 'Integrity guard tests passed.\n'
