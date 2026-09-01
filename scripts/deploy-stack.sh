#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  printf 'Usage: %s STACK [--check] [--inventory production|lab] [--ref GIT_REF]\n' "$0" >&2
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    printf 'ERROR: required command not found: %s\n' "$1" >&2
    exit 1
  }
}

if (($# < 1)); then
  usage
  exit 2
fi

if ((EUID == 0)); then
  printf 'ERROR: run Git and Ansible as a normal operator, not root.\n' >&2
  exit 1
fi

stack="$1"
shift
inventory="production"
git_ref="HEAD"
check_mode=0

[[ "$stack" =~ ^[a-z0-9][a-z0-9-]*$ ]] || {
  printf 'ERROR: unsafe stack name: %s\n' "$stack" >&2
  exit 2
}

while (($#)); do
  case "$1" in
    --check)
      check_mode=1
      shift
      ;;
    --inventory)
      (($# >= 2)) || { usage; exit 2; }
      inventory="$2"
      shift 2
      ;;
    --ref)
      (($# >= 2)) || { usage; exit 2; }
      git_ref="$2"
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

case "$inventory" in
  production)
    production_operation=1
    ;;
  lab)
    production_operation=0
    ;;
  *)
    printf 'ERROR: unsupported inventory: %s\n' "$inventory" >&2
    exit 2
    ;;
esac

for required_command in ansible-inventory ansible-playbook flock git python3 sudo tar; do
  require_command "$required_command"
done

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"
git rev-parse --is-inside-work-tree >/dev/null

if [[ "$inventory" == "lab" ]]; then
  [[ -n "${HOMELAB_LAB_HOSTNAME:-}" ]] || {
    printf 'ERROR: set HOMELAB_LAB_HOSTNAME to the exact Lab hostname.\n' >&2
    exit 1
  }
fi

if [[ "$git_ref" != "HEAD" ]] && ! git check-ref-format --branch "$git_ref" >/dev/null 2>&1; then
  printf 'ERROR: unsafe or invalid Git ref: %s\n' "$git_ref" >&2
  exit 2
fi

git cat-file -e "${git_ref}^{commit}"
release_commit="$(git rev-parse "${git_ref}^{commit}")"

runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
[[ -d "$runtime_dir" && "$(stat -c %u "$runtime_dir")" == "$(id -u)" ]] || {
  printf 'ERROR: a private operator runtime directory is required: %s\n' "$runtime_dir" >&2
  exit 1
}
exec {deployment_lock_fd}>"$runtime_dir/homelab-ops-deploy.lock"
if ! flock -n "$deployment_lock_fd"; then
  printf 'ERROR: another HomeLab deployment is already running.\n' >&2
  exit 1
fi

# Current main is always the trusted control plane. Historical refs provide
# stack payload only; old inventories, roles and helper scripts are never run.
if ((production_operation == 1)); then
  [[ -z "$(git status --porcelain --untracked-files=all)" ]] || {
    printf 'ERROR: refusing Production operation from a dirty working tree.\n' >&2
    exit 1
  }
  [[ "$(git branch --show-current)" == "main" ]] || {
    printf 'ERROR: Production operations must use the current main control plane.\n' >&2
    exit 1
  }
  git fetch --quiet origin main
  [[ "$(git rev-parse 'HEAD^{commit}')" == "$(git rev-parse 'origin/main^{commit}')" ]] || {
    printf 'ERROR: local main control plane is not exactly origin/main.\n' >&2
    exit 1
  }
fi

if [[ "$git_ref" == "HEAD" ]]; then
  [[ -z "$(git status --porcelain --untracked-files=all)" ]] || {
    printf 'ERROR: refusing to deploy HEAD from a dirty working tree.\n' >&2
    exit 1
  }
elif ((production_operation == 1)) && [[ ! "$git_ref" =~ ^release-[0-9]{8}-[0-9]{6}Z$ ]]; then
  printf 'ERROR: Production --ref accepts only an exact verified release tag.\n' >&2
  exit 1
fi

if ((production_operation == 1)) && [[ "$git_ref" != "HEAD" ]]; then
  git show-ref --verify --quiet "refs/tags/$git_ref" || {
    printf 'ERROR: Production ref is not a local tag: %s\n' "$git_ref" >&2
    exit 1
  }
  [[ "$(git cat-file -t "refs/tags/$git_ref")" == "tag" ]] || {
    printf 'ERROR: Production rollback requires an annotated tag.\n' >&2
    exit 1
  }
  release_commit="$(git rev-parse "refs/tags/$git_ref^{commit}")"
fi

release_root="$repo_root"
tmp_root=""
cleanup() {
  [[ -z "${tmp_root:-}" ]] || rm -rf -- "$tmp_root"
}
trap cleanup EXIT

if [[ "$git_ref" != "HEAD" ]]; then
  git cat-file -e "${release_commit}:stacks/$stack/stack.yml" 2>/dev/null || {
    printf 'ERROR: stack is not managed at ref %s: %s\n' "$git_ref" "$stack" >&2
    exit 1
  }
  tmp_root="$(mktemp -d /tmp/homelab-ops-release.XXXXXXXX)"
  git archive "$release_commit" "stacks/$stack" | tar -x -C "$tmp_root"
  release_root="$tmp_root"
fi

stack_contract="$release_root/stacks/$stack/stack.yml"
[[ -f "$stack_contract" ]] || {
  printf 'ERROR: stack release payload is unavailable at ref %s: %s\n' "$git_ref" "$stack" >&2
  exit 1
}

if ((production_operation == 1)); then
  readiness_args=(
    "$repo_root/scripts/check-recovery-readiness.py"
    "$stack_contract"
    --forbid-evidence-under "$repo_root"
  )
  current_stack_contract="$repo_root/stacks/$stack/stack.yml"
  if [[ -f "$current_stack_contract" ]]; then
    readiness_args+=(--current-contract "$current_stack_contract")
  fi
  if [[ -n "${HOMELAB_RECOVERY_EVIDENCE:-}" ]]; then
    readiness_args+=(--evidence "$HOMELAB_RECOVERY_EVIDENCE")
  fi
  if [[ -n "${HOMELAB_BACKUP_MAX_AGE_SECONDS:-}" ]]; then
    readiness_args+=(--max-backup-age-seconds "$HOMELAB_BACKUP_MAX_AGE_SECONDS")
  fi
  python3 "${readiness_args[@]}"
fi

inventory_file="$repo_root/ansible/inventory/$inventory/hosts.yml"
[[ -f "$inventory_file" ]] || {
  printf 'ERROR: inventory file missing: %s\n' "$inventory_file" >&2
  exit 1
}

export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"
bash "$repo_root/scripts/assert-ansible-hosts.sh" "$inventory_file"

become_args=()
if ((production_operation == 1)) && ! sudo -n true >/dev/null 2>&1; then
  become_args+=(--ask-become-pass)
fi

ansible-playbook -i "$inventory_file" \
  "$repo_root/ansible/playbooks/preflight.yml" \
  -e "stack_name=$stack" \
  -e "homelab_repo_root=$repo_root" \
  -e "homelab_release_root=$release_root" \
  "${become_args[@]}"

deploy_args=(
  -i "$inventory_file"
  "$repo_root/ansible/playbooks/deploy-stack.yml"
  -e "stack_name=$stack"
  -e "homelab_release_commit=$release_commit"
  -e "homelab_repo_root=$repo_root"
  -e "homelab_release_root=$release_root"
  "${become_args[@]}"
)

if ((check_mode == 1)); then
  deploy_args+=(--check --diff)
fi

ansible-playbook "${deploy_args[@]}"
