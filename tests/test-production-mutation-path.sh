#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
deploy="$repo_root/scripts/deploy-stack.sh"
rollback="$repo_root/scripts/rollback-stack.sh"
deploy_playbook="$repo_root/ansible/playbooks/deploy-stack.yml"
preflight_playbook="$repo_root/ansible/playbooks/preflight.yml"
managed_role="$repo_root/ansible/roles/managed_stack/tasks/main.yml"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

lock_call="flock -n \"\$deployment_lock_fd\""
rollback_exec="exec bash \"\$script_dir/deploy-stack.sh\" \"\$1\" --ref \"\$2\""

grep -Fq -- 'homelab-ops-deploy.lock' "$deploy" || fail 'deploy path must use the shared deployment lock'
grep -Fq -- "$lock_call" "$deploy" || fail 'deployment lock must fail closed instead of waiting or running concurrently'
grep -Fq -- "$rollback_exec" "$rollback" || fail 'explicit rollback must reuse the guarded deployment path'
grep -Fq -- 'check-recovery-readiness.py' "$deploy" || fail 'Production deployment must invoke the recovery readiness gate'
grep -Fq -- '--current-contract' "$deploy" || fail 'historical payloads must be checked against current stateful classification'
grep -Fq -- '--forbid-evidence-under' "$deploy" || fail 'private readiness evidence must stay outside the public repository tree'
grep -Fq -- 'HOMELAB_RECOVERY_EVIDENCE' "$deploy" || fail 'Production stateful readiness must consume private evidence'
grep -Fq -- 'HOMELAB_BACKUP_MAX_AGE_SECONDS' "$deploy" || fail 'Production stateful readiness must consume environment freshness policy'

grep -Fq -- 'validate-stack-contracts.py' "$deploy" || fail 'selected release payload must use the current contract validator'
grep -Fq -- '--stack-dir' "$deploy" || fail 'deployment must validate the exact selected stack directory'
grep -Fq -- 'git ls-remote --tags origin' "$deploy" || fail 'Production release tags must be checked against origin'
grep -Fq -- 'git merge-base --is-ancestor' "$deploy" || fail 'Production release commits must belong to origin/main history'

grep -Fq -- 'name: homelab_stack_contract' "$deploy_playbook" || fail 'stack.yml must be loaded into a namespace'
if grep -Fq -- 'file: "{{ stack_source_dir }}/stack.yml"' "$preflight_playbook"; then
  fail 'preflight must not load stack.yml into play variables'
fi

grep -Fq -- 'stack_retired_dests' "$managed_role" || fail 'forward convergence must track files removed from the managed boundary'
grep -Fq -- 'Remove files no longer managed by the candidate' "$managed_role" || fail 'forward convergence must remove retired managed files'
remove_orphans_count="$(grep -Fc -- '--remove-orphans' "$managed_role")"
((remove_orphans_count >= 2)) || fail 'candidate apply and rollback must both remove orphan Compose services'

if grep -Eq -- '--routine-update|routine_update|maintenance-bypass|skip-recovery|skip-readiness' "$deploy" "$rollback"; then
  fail 'Production wrappers must not expose a routine-maintenance safety bypass'
fi

printf 'Production mutation path invariants passed.\n'
