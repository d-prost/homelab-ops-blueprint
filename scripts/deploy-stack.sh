#!/usr/bin/env bash
set -Eeuo pipefail
usage() { printf 'Usage: %s STACK [--check] [--inventory production|lab] [--ref GIT_REF]\n' "$0" >&2; }
if (($# < 1)); then usage; exit 2; fi
if ((EUID == 0)); then printf 'ERROR: run Git and Ansible as a normal operator, not root.\n' >&2; exit 1; fi
stack="$1"; shift
inventory="production"; git_ref="HEAD"; check_mode=0
[[ "$stack" =~ ^[a-z0-9][a-z0-9-]*$ ]] || exit 2
while (($#)); do
  case "$1" in
    --check) check_mode=1; shift ;;
    --inventory) (($# >= 2)) || { usage; exit 2; }; inventory="$2"; shift 2 ;;
    --ref) (($# >= 2)) || { usage; exit 2; }; git_ref="$2"; shift 2 ;;
    *) usage; exit 2 ;;
  esac
done
case "$inventory" in production|lab) ;; *) exit 2 ;; esac
for cmd in ansible-inventory ansible-playbook flock git python3 sudo tar; do command -v "$cmd" >/dev/null || { printf 'ERROR: missing command: %s\n' "$cmd" >&2; exit 1; }; done
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"; git rev-parse --is-inside-work-tree >/dev/null
if [[ "$inventory" == "lab" ]]; then [[ -n "${HOMELAB_LAB_HOSTNAME:-}" ]] || { printf 'ERROR: set HOMELAB_LAB_HOSTNAME to the exact Lab hostname.\n' >&2; exit 1; }; fi
if [[ "$git_ref" != "HEAD" ]] && ! git check-ref-format --branch "$git_ref" >/dev/null 2>&1; then printf 'ERROR: unsafe Git ref.\n' >&2; exit 2; fi
git cat-file -e "${git_ref}^{commit}"; release_commit="$(git rev-parse "${git_ref}^{commit}")"
runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
[[ -d "$runtime_dir" && "$(stat -c %u "$runtime_dir")" == "$(id -u)" ]] || { printf 'ERROR: private operator runtime directory required: %s\n' "$runtime_dir" >&2; exit 1; }
exec {lock_fd}>"$runtime_dir/homelab-ops-deploy.lock"
flock -n "$lock_fd" || { printf 'ERROR: another deployment is running.\n' >&2; exit 1; }
if [[ "$git_ref" == "HEAD" ]]; then
  [[ -z "$(git status --porcelain --untracked-files=all)" ]] || { printf 'ERROR: refusing dirty working tree.\n' >&2; exit 1; }
  if [[ "$inventory" == "production" ]]; then
    [[ "$(git branch --show-current)" == "main" ]] || { printf 'ERROR: Production HEAD deployments require main.\n' >&2; exit 1; }
    git fetch --quiet origin main
    [[ "$release_commit" == "$(git rev-parse 'origin/main^{commit}')" ]] || { printf 'ERROR: local main is not exactly origin/main.\n' >&2; exit 1; }
  fi
elif [[ "$inventory" == "production" && ! "$git_ref" =~ ^release-[0-9]{8}-[0-9]{6}Z$ ]]; then printf 'ERROR: Production --ref accepts only verified release tags.\n' >&2; exit 1; fi
if [[ "$inventory" == "production" && "$git_ref" != "HEAD" ]]; then
  git show-ref --verify --quiet "refs/tags/$git_ref" || exit 1
  [[ "$(git cat-file -t "refs/tags/$git_ref")" == "tag" ]] || { printf 'ERROR: rollback requires an annotated tag.\n' >&2; exit 1; }
  release_commit="$(git rev-parse "refs/tags/$git_ref^{commit}")"
fi
deployment_root="$repo_root"; tmp_root=""
if [[ "$git_ref" != "HEAD" ]]; then tmp_root="$(mktemp -d /tmp/homelab-ops-release.XXXXXXXX)"; trap '[[ -n "${tmp_root:-}" ]] && rm -rf -- "$tmp_root"' EXIT; git archive "$release_commit" | tar -x -C "$tmp_root"; deployment_root="$tmp_root"; fi
[[ -f "$deployment_root/stacks/$stack/stack.yml" ]] || { printf 'ERROR: unknown managed stack: %s\n' "$stack" >&2; exit 1; }
inventory_file="$deployment_root/ansible/inventory/$inventory/hosts.yml"
[[ -f "$inventory_file" ]] || { printf 'ERROR: inventory file missing: %s\n' "$inventory_file" >&2; exit 1; }
export ANSIBLE_CONFIG="$deployment_root/ansible/ansible.cfg"
bash "$deployment_root/scripts/assert-ansible-hosts.sh" "$inventory_file"
become_args=(); if [[ "$inventory" == "production" ]] && ! sudo -n true >/dev/null 2>&1; then become_args+=(--ask-become-pass); fi
ansible-playbook -i "$inventory_file" "$deployment_root/ansible/playbooks/preflight.yml" -e "stack_name=$stack" -e "homelab_repo_root=$deployment_root" "${become_args[@]}"
deploy_args=(-i "$inventory_file" "$deployment_root/ansible/playbooks/deploy-stack.yml" -e "stack_name=$stack" -e "homelab_release_commit=$release_commit" -e "homelab_repo_root=$deployment_root" "${become_args[@]}")
if ((check_mode)); then deploy_args+=(--check --diff); fi
ansible-playbook "${deploy_args[@]}"
