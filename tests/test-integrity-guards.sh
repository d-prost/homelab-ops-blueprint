#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
grep -q 'check_mode: false' "$repo_root/ansible/playbooks/deploy-stack.yml"
grep -q 'check_mode: false' "$repo_root/ansible/playbooks/preflight.yml"
grep -Eq '^roles_path[[:space:]]*=[[:space:]]*\./roles[[:space:]]*$' "$repo_root/ansible/ansible.cfg"
grep -q 'local main control plane is not exactly origin/main' "$repo_root/scripts/deploy-stack.sh"
grep -q 'prior managed files were restored' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'stack_functional_checks' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'delegate_to: localhost' "$repo_root/ansible/playbooks/preflight.yml"
grep -q 'ansible.builtin.script:' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'Load exact prior contract from Git history' "$repo_root/ansible/roles/managed_stack/tasks/main.yml"
grep -q 'Historical refs provide' "$repo_root/scripts/deploy-stack.sh"
grep -q 'MANIFEST.tsv differs from stack.yml' "$repo_root/scripts/validate-stack-contracts.py"
printf 'Integrity guard tests passed.\n'
