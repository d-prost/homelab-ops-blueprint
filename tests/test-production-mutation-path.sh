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

rollback_exec="exec bash \"\$script_dir/deploy-stack.sh\" \"\$1\" --ref \"\$2\""

grep -Fq -- 'target-lock-key.py' "$deploy" || fail 'deployment must derive a stable declared-target lock key'
grep -Fq -- '/run/lock/homelab-ops-' "$deploy" || fail 'deployment lock must live in the host-global lock namespace'
grep -Fq -- 'lock-utils.sh' "$deploy" || fail 'deployment must use the shared host-global lock primitive'
grep -Fq -- 'homelab_acquire_global_lock' "$deploy" || fail 'deployment must acquire the host-global target/stack lock'
grep -Fq -- 'PRE_MUTATION_REFUSAL: another transaction already holds the target/stack lock' "$deploy" || fail 'lock contention must refuse before mutation'
if grep -Fq -- 'XDG_RUNTIME_DIR' "$deploy"; then
  fail 'Production serialization must not depend on a user-specific runtime directory'
fi
lock_line="$(grep -nF 'homelab_acquire_global_lock' "$deploy" | head -n1 | cut -d: -f1)"
preflight_line="$(grep -nF 'ansible/playbooks/preflight.yml' "$deploy" | head -n1 | cut -d: -f1)"
[[ -n "$lock_line" && -n "$preflight_line" ]] || fail 'unable to locate lock and target preflight boundaries'
((lock_line < preflight_line)) || fail 'target/stack lock must be acquired before remote preflight'
grep -Fq -- "$rollback_exec" "$rollback" || fail 'explicit rollback must reuse the guarded deployment path'
grep -Fq -- 'check-recovery-readiness.py' "$deploy" || fail 'Production deployment must invoke the recovery readiness gate'
grep -Fq -- 'ANSIBLE_HOST_KEY_CHECKING=True' "$deploy" || fail 'Production wrapper must force Ansible host-key checking on'
grep -Fq -- 'validate-target-inventory.py' "$deploy" || fail 'Production inventory transport policy must be validated before connection'
grep -Fq -- 'PRE_MUTATION_REFUSAL: transport or target preflight failed' "$deploy" || fail 'transport or target identity failure must be classified before mutation'
grep -Fq -- 'unresolved transaction state exists' "$preflight_playbook" || fail 'unresolved acceptance state must block a new transaction before mutation'
grep -Fq -- 'stack_runtime_verified: true' "$managed_role" || fail 'runtime PASS must be explicit before acceptance commit'
grep -Fq -- 'Commit acceptance record atomically and durably' "$managed_role" || fail 'acceptance must use the durable atomic commit helper'
grep -Fq -- 'ACCEPTANCE_PERSISTENCE_FAILED' "$managed_role" || fail 'record persistence failure must have an explicit terminal result'
grep -Fq -- 'automatic rollback is intentionally not attempted' "$managed_role" || fail 'acceptance persistence failure must not auto-rollback'
marker_commit_line="$(grep -nF 'Commit unresolved transaction marker durably before mutation' "$managed_role" | head -n1 | cut -d: -f1)"
managed_install_line="$(grep -nF 'Install allowlisted managed files atomically' "$managed_role" | head -n1 | cut -d: -f1)"
runtime_verify_line="$(grep -nF 'Run functional stack verification on the target' "$managed_role" | head -n1 | cut -d: -f1)"
acceptance_commit_line="$(grep -nF 'Commit acceptance record atomically and durably' "$managed_role" | head -n1 | cut -d: -f1)"
accepted_report_line="$(grep -nF 'Report durable acceptance' "$managed_role" | head -n1 | cut -d: -f1)"
[[ -n "$marker_commit_line" && -n "$managed_install_line" && -n "$runtime_verify_line" && -n "$acceptance_commit_line" && -n "$accepted_report_line" ]] || fail 'unable to locate transaction acceptance boundaries'
((marker_commit_line < managed_install_line)) || fail 'durable unresolved marker must precede managed mutation'
((managed_install_line < runtime_verify_line)) || fail 'functional verification must follow managed mutation'
((runtime_verify_line < acceptance_commit_line)) || fail 'acceptance record must be committed only after runtime verification'
((acceptance_commit_line < accepted_report_line)) || fail 'ACCEPTED must be reported only after durable record commit'
grep -Fq -- '--current-contract' "$deploy" || fail 'historical payloads must be checked against current stateful classification'
grep -Fq -- '--forbid-evidence-under' "$deploy" || fail 'private readiness evidence must stay outside the public repository tree'
grep -Fq -- 'HOMELAB_RECOVERY_EVIDENCE' "$deploy" || fail 'Production stateful readiness must consume private evidence'
grep -Fq -- 'HOMELAB_BACKUP_MAX_AGE_SECONDS' "$deploy" || fail 'Production stateful readiness must consume environment freshness policy'

grep -Fq -- 'validate-stack-contracts.py' "$deploy" || fail 'selected release payload must use the current contract validator'
grep -Fq -- 'materialize-git-snapshot.sh' "$deploy" || fail 'deployment must freeze Git payloads before mutation'
grep -Fq -- 'validate-stack-contracts.py" --stack-dir' "$deploy" || fail 'previous accepted payload must be revalidated before mutation'
grep -Fq -- 'render-stack-images.py' "$deploy" || fail 'frozen candidate and rollback images must be rendered before mutation'
grep -Fq -- 'preflight-images.yml' "$deploy" || fail 'runtime image availability must be proven before managed mutation'
grep -Fq -- 'PRE_MUTATION_REFUSAL: previous accepted Git material is unavailable' "$deploy" || fail 'missing rollback Git material must fail as a pre-mutation refusal'
grep -Fq -- 'PRE_MUTATION_REFUSAL: required runtime image is unavailable by digest' "$deploy" || fail 'image unavailability must fail as a pre-mutation refusal'
artifact_preflight_line="$(grep -nF 'preflight-images.yml' "$deploy" | head -n1 | cut -d: -f1)"
managed_deploy_line="$(grep -nF 'deploy_args=(' "$deploy" | head -n1 | cut -d: -f1)"
[[ -n "$artifact_preflight_line" && -n "$managed_deploy_line" ]] || fail 'unable to locate artifact preflight and managed deploy boundaries'
((artifact_preflight_line < managed_deploy_line)) || fail 'runtime artifact preflight must occur before managed deployment begins'
grep -Fq -- 'read-accepted-record.yml' "$deploy" || fail 'deployment must resolve previous accepted state before mutation'
grep -Fq -- 'homelab_tooling_commit' "$deploy" || fail 'deployment must carry an independent tooling commit'
grep -Fq -- 'homelab_previous_release_root' "$deploy" || fail 'deployment must pass a frozen previous accepted payload'
if grep -Fq -- '/usr/bin/git' "$managed_role"; then
  fail 'managed role must not consult Git after transaction preparation'
fi
grep -Fq -- '--stack-dir' "$deploy" || fail 'deployment must validate the exact selected stack directory'
grep -Fq -- 'git ls-remote --tags origin' "$deploy" || fail 'Production release tags must be checked against origin'
grep -Fq -- 'git merge-base --is-ancestor' "$deploy" || fail 'Production release commits must belong to origin/main history'

grep -Fq -- 'name: homelab_stack_contract' "$deploy_playbook" || fail 'stack.yml must be loaded into a namespace'
if grep -Fq -- 'file: "{{ stack_source_dir }}/stack.yml"' "$preflight_playbook"; then
  fail 'preflight must not load stack.yml into play variables'
fi

grep -Fq -- 'stack_retired_dests' "$managed_role" || fail 'forward convergence must track files removed from the managed boundary'
grep -Fq -- 'Stage frozen prior managed files for transaction rollback' "$managed_role" || fail 'rollback must use the frozen accepted payload'
grep -Fq -- 'Remove files no longer managed by the candidate' "$managed_role" || fail 'forward convergence must remove retired managed files'
remove_orphans_count="$(grep -Fc -- '--remove-orphans' "$managed_role")"
((remove_orphans_count >= 2)) || fail 'candidate apply and rollback must both remove orphan Compose services'

if grep -Eq -- '--routine-update|routine_update|maintenance-bypass|skip-recovery|skip-readiness' "$deploy" "$rollback"; then
  fail 'Production wrappers must not expose a routine-maintenance safety bypass'
fi

printf 'Production mutation path invariants passed.\n'
