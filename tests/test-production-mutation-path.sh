#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
deploy="$repo_root/scripts/deploy-stack.sh"
rollback="$repo_root/scripts/rollback-stack.sh"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

lock_call="flock -n \"\$deployment_lock_fd\""
rollback_exec="exec bash \"\$script_dir/deploy-stack.sh\" \"\$1\" --ref \"\$2\""

grep -Fq -- 'homelab-ops-deploy.lock' "$deploy" || fail 'deploy path must use the shared deployment lock'
grep -Fq -- "$lock_call" "$deploy" || fail 'deployment lock must fail closed instead of waiting or running concurrently'
grep -Fq -- "$rollback_exec" "$rollback" || fail 'explicit rollback must reuse the guarded deployment path'

if grep -Eq -- '--routine-update|routine_update|maintenance-bypass|skip-recovery' "$deploy" "$rollback"; then
  fail 'Production wrappers must not expose a routine-maintenance safety bypass'
fi

printf 'Production mutation path invariants passed.\n'
