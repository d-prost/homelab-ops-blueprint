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

  remote_tag_record="$(git ls-remote --tags origin "refs/tags/$git_ref^{}")"
  [[ -n "$remote_tag_record" ]] || {
    printf 'ERROR: release tag is not published on origin: %s\n' "$git_ref" >&2
    exit 1
  }
  read -r remote_release_commit _ <<<"$remote_tag_record"
  [[ "$remote_release_commit" == "$release_commit" ]] || {
    printf 'ERROR: local release tag does not match origin: %s\n' "$git_ref" >&2
    exit 1
  }
  if ! git merge-base --is-ancestor "$release_commit" origin/main; then
    printf 'ERROR: release commit is not part of origin/main history: %s\n' "$git_ref" >&2
    exit 1
  fi
fi

tooling_commit="$(git rev-parse 'HEAD^{commit}')"
if [[ "$git_ref" == "HEAD" ]]; then
  release_commit="$tooling_commit"
else
  release_commit="$(git rev-parse "refs/tags/$git_ref^{commit}")"
fi

transaction_id="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
transaction_root="$(mktemp -d /tmp/homelab-ops-transaction.XXXXXXXX)"
release_root="$transaction_root/candidate"
previous_release_root=""
previous_accepted_commit=""
previous_record_id=""

cleanup() {
  rm -rf -- "$transaction_root"
}
trap cleanup EXIT

bash "$repo_root/scripts/materialize-git-snapshot.sh" \
  "$repo_root" "$release_commit" "$release_root" "stacks/$stack" >/dev/null

stack_dir="$release_root/stacks/$stack"
stack_contract="$stack_dir/stack.yml"
[[ -f "$stack_contract" ]] || {
  printf 'ERROR: stack release payload is unavailable at ref %s: %s\n' "$git_ref" "$stack" >&2
  exit 1
}

# Every selected payload is re-validated by the current control plane, including
# historical release tags used for rollback.
python3 "$repo_root/scripts/validate-stack-contracts.py" --stack-dir "$stack_dir"

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

ansible-playbook -i "$inventory_file" \
  "$repo_root/ansible/playbooks/read-accepted-record.yml" \
  -e "stack_name=$stack" \
  -e "homelab_transaction_root=$transaction_root" \
  "${become_args[@]}"

if [[ -f "$transaction_root/previous.record" ]]; then
  mapfile -t previous_commit_matches < <(
    sed -nE 's/^commit=([0-9a-f]{40})$/\1/p' "$transaction_root/previous.record"
  )
  (("${#previous_commit_matches[@]}" == 1)) || {
    printf 'ERROR: prior deployment record does not contain exactly one valid commit.\n' >&2
    exit 1
  }
  previous_accepted_commit="${previous_commit_matches[0]}"
  previous_record_id="$(sha256sum "$transaction_root/previous.record" | awk '{print $1}')"
  previous_release_root="$transaction_root/previous"
  bash "$repo_root/scripts/materialize-git-snapshot.sh" \
    "$repo_root" "$previous_accepted_commit" "$previous_release_root" "stacks/$stack" >/dev/null
fi

contract_hash="$(sha256sum "$stack_contract" | awk '{print $1}')"
manifest_hash="$(sha256sum "$stack_dir/MANIFEST.tsv" | awk '{print $1}')"

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
  -e "homelab_tooling_commit=$tooling_commit"
  -e "homelab_transaction_id=$transaction_id"
  -e "homelab_contract_hash=$contract_hash"
  -e "homelab_manifest_hash=$manifest_hash"
  -e "homelab_previous_accepted_commit=$previous_accepted_commit"
  -e "homelab_previous_record_id=$previous_record_id"
  -e "homelab_previous_release_root=$previous_release_root"
  -e "homelab_repo_root=$repo_root"
  -e "homelab_release_root=$release_root"
  "${become_args[@]}"
)

if ((check_mode == 1)); then
  deploy_args+=(--check --diff)
fi

ansible-playbook "${deploy_args[@]}"
