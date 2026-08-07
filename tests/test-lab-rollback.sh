#!/usr/bin/env bash
set -Eeuo pipefail
[[ "${HOMELAB_LAB_ROLLBACK_TEST:-0}" == "1" ]] || { printf 'ERROR: set HOMELAB_LAB_ROLLBACK_TEST=1.\n' >&2; exit 1; }
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"; cd "$repo_root"
actual_hostname="$(hostname)"; export HOMELAB_LAB_HOSTNAME="$actual_hostname"
target_dir="/opt/homelab-ops/stacks/dozzle"; record_file="/etc/homelab-ops/deployments/dozzle.record"; network_name="homelab_ops_demo"; tmp_root="$(mktemp -d)"; runtime_dir="$tmp_root/runtime"; failure_log="$tmp_root/failed-deploy.log"; network_created=0
[[ ! -e "$target_dir" ]] || { printf 'ERROR: disposable Lab target already exists: %s\n' "$target_dir" >&2; exit 1; }
cleanup(){ set +e; if [[ -f "$target_dir/docker-compose.yml" && -f "$target_dir/defaults.env" ]]; then sudo /usr/bin/docker compose --env-file "$target_dir/defaults.env" -f "$target_dir/docker-compose.yml" down --remove-orphans >/dev/null 2>&1; fi; sudo rm -rf -- "$target_dir"; sudo rm -f -- "$record_file"; if ((network_created)); then sudo /usr/bin/docker network rm "$network_name" >/dev/null 2>&1; fi; rm -rf -- "$tmp_root"; }; trap cleanup EXIT
mkdir -p "$runtime_dir"; chmod 0700 "$runtime_dir"
if ! sudo /usr/bin/docker network inspect "$network_name" >/dev/null 2>&1; then sudo /usr/bin/docker network create "$network_name" >/dev/null; network_created=1; fi
export XDG_RUNTIME_DIR="$runtime_dir"; export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"
bash scripts/deploy-stack.sh dozzle --inventory lab
before_compose="$(sudo sha256sum "$target_dir/docker-compose.yml" | awk '{print $1}')"; before_defaults="$(sudo sha256sum "$target_dir/defaults.env" | awk '{print $1}')"
git archive HEAD | tar -x -C "$tmp_root"
python3 - "$tmp_root/stacks/dozzle/compose.yaml" <<'PY_INNER'
from pathlib import Path
import sys, yaml
path=Path(sys.argv[1]); model=yaml.safe_load(path.read_text()); model['services']['dozzle']['entrypoint']=['/bin/sh','-c','exit 42']; path.write_text(yaml.safe_dump(model,sort_keys=False))
PY_INNER
set +e
ANSIBLE_CONFIG="$tmp_root/ansible/ansible.cfg" ansible-playbook -i "$tmp_root/ansible/inventory/lab/hosts.yml" "$tmp_root/ansible/playbooks/deploy-stack.yml" -e stack_name=dozzle -e homelab_release_commit=1111111111111111111111111111111111111111 -e homelab_repo_root="$tmp_root" >"$failure_log" 2>&1
failed_rc=$?; set -e
((failed_rc != 0)) || { cat "$failure_log" >&2; exit 1; }
grep -q 'previous managed files were restored' "$failure_log" || { cat "$failure_log" >&2; exit 1; }
after_compose="$(sudo sha256sum "$target_dir/docker-compose.yml" | awk '{print $1}')"; after_defaults="$(sudo sha256sum "$target_dir/defaults.env" | awk '{print $1}')"
[[ "$before_compose" == "$after_compose" ]]; [[ "$before_defaults" == "$after_defaults" ]]
sudo /usr/bin/python3 "$repo_root/scripts/verify-compose-health.py" --stack-dir "$target_dir" --compose-file docker-compose.yml --env-file defaults.env --contract "$repo_root/stacks/dozzle/stack.yml"
printf 'Ephemeral Lab rollback proof passed.\n'
