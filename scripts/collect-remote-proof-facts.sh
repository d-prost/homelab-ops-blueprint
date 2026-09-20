#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  printf 'Usage: HOMELAB_REMOTE_PROOF=1 %s /absolute/path/to/private-hosts.yml\n' "$0" >&2
}

[[ "${HOMELAB_REMOTE_PROOF:-0}" == "1" ]] || {
  printf 'ERROR: set HOMELAB_REMOTE_PROOF=1 to authorize this read-only remote proof preparation.\n' >&2
  exit 1
}

(($# == 1)) || { usage; exit 2; }
inventory="$1"
[[ "$inventory" == /* && -f "$inventory" ]] || {
  printf 'ERROR: inventory must be an absolute readable file outside the repository workflow.\n' >&2
  exit 2
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

for cmd in ansible ansible-inventory ansible-playbook python3; do
  command -v "$cmd" >/dev/null 2>&1 || {
    printf 'ERROR: required command not found: %s\n' "$cmd" >&2
    exit 1
  }
done

export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"
export ANSIBLE_HOST_KEY_CHECKING=True

python3 - "$inventory" <<'PY'
import json
import subprocess
import sys

inventory = sys.argv[1]
result = subprocess.run(
    ["ansible-inventory", "-i", inventory, "--list"],
    text=True,
    capture_output=True,
)
if result.returncode:
    raise SystemExit(result.stderr or result.stdout)
doc = json.loads(result.stdout)
hostvars = doc.get("_meta", {}).get("hostvars", {})
if len(hostvars) != 1:
    raise SystemExit(f"ERROR: remote proof requires exactly one host, got {len(hostvars)}")
name, values = next(iter(hostvars.items()))
if values.get("ansible_connection", "ssh") != "ssh":
    raise SystemExit("ERROR: remote proof target must use SSH")
if values.get("homelab_environment") != "lab":
    raise SystemExit("ERROR: remote proof inventory must classify the target as lab")
if not values.get("homelab_expected_hostname"):
    raise SystemExit("ERROR: homelab_expected_hostname is required")
print("Inventory policy: PASS (one separate SSH lab target)")
PY

ansible-playbook -i "$inventory" "$repo_root/ansible/playbooks/preflight.yml"   -e stack_name=dozzle   -e "homelab_repo_root=$repo_root"   -e "homelab_release_root=$repo_root" >/dev/null

printf 'Target identity + Docker preflight: PASS\n'
printf 'Topology: separate SSH target\n'
printf 'Control Ansible: '
ansible --version | head -n1 | sed -E 's/\[[^]]*\]//g'

printf 'Target OS: '
ansible all -i "$inventory" -b -m ansible.builtin.shell   -a '. /etc/os-release && printf "%s %s" "$NAME" "$VERSION_ID"'   -o | sed -E 's/^[^|]+\|[^>]+>>[[:space:]]*//' | tail -n1

printf 'Docker Engine: '
ansible all -i "$inventory" -b -m ansible.builtin.command   -a '/usr/bin/docker version --format {{.Server.Version}}'   -o | sed -E 's/^[^|]+\|[^>]+>>[[:space:]]*//' | tail -n1

printf 'Docker Compose: '
ansible all -i "$inventory" -b -m ansible.builtin.command   -a '/usr/bin/docker compose version --short'   -o | sed -E 's/^[^|]+\|[^>]+>>[[:space:]]*//' | tail -n1

printf 'Repository commit: %s\n' "$(git rev-parse HEAD)"
printf 'Readiness collection complete. This is not the transaction proof; execute docs/REMOTE_SSH_PROOF.md before closing issue #35.\n'
