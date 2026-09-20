#!/usr/bin/env bash
set -Eeuo pipefail

[[ "${HOMELAB_LAB_FAILURE_MATRIX_TEST:-0}" == "1" ]] || {
  printf 'ERROR: set HOMELAB_LAB_FAILURE_MATRIX_TEST=1.\n' >&2
  exit 1
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"
export HOMELAB_LAB_HOSTNAME
HOMELAB_LAB_HOSTNAME="$(/bin/hostname)"
export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"

target_dir="/opt/homelab-ops/stacks/dozzle"
record_file="/etc/homelab-ops/deployments/dozzle.record"
receipt_file="/etc/homelab-ops/deployments/dozzle.receipt"
marker_file="/var/lib/homelab-ops/transactions/dozzle.unresolved"
tmp_root="$(mktemp -d)"
baseline_root="$tmp_root/baseline"

cleanup() {
  set +e
  if [[ -f "$target_dir/docker-compose.yml" && -f "$target_dir/defaults.env" ]]; then
    sudo /usr/bin/docker compose --env-file "$target_dir/defaults.env" -f "$target_dir/docker-compose.yml" down --remove-orphans >/dev/null 2>&1
  fi
  sudo rm -rf -- "$target_dir" /var/lib/homelab-ops/candidates/dozzle-*
  sudo rm -f -- "$record_file" "$receipt_file" "$marker_file"
  rm -rf -- "$tmp_root"
}
trap cleanup EXIT

[[ ! -e "$target_dir" ]] || { printf 'ERROR: disposable target exists.\n' >&2; exit 1; }

mkdir -p "$baseline_root"
git archive HEAD | tar -x -C "$baseline_root"
python3 - "$baseline_root/stacks/dozzle" <<'PY'
from pathlib import Path
import sys, yaml
stack=Path(sys.argv[1])
(stack/"retired.txt").write_text("retire me\n",encoding="utf-8")
contract_path=stack/"stack.yml"
contract=yaml.safe_load(contract_path.read_text())
contract["stack_managed_files"].append({"src":"retired.txt","dest":"retired.txt","mode":"0640"})
contract_path.write_text(yaml.safe_dump(contract,sort_keys=False))
with (stack/"MANIFEST.tsv").open("a",encoding="utf-8") as h:
    h.write(f"retired.txt\t{contract['stack_target_dir']}/retired.txt\n")
PY

invoke() {
  local release_root="$1" tx="$2" release_commit="$3" prev_commit="$4" prev_id="$5" prev_source="$6" prev_root="$7"
  local contract_hash manifest_hash
  contract_hash="$(sha256sum "$release_root/stacks/dozzle/stack.yml" | awk '{print $1}')"
  manifest_hash="$(sha256sum "$release_root/stacks/dozzle/MANIFEST.tsv" | awk '{print $1}')"
  ansible-playbook -i "$repo_root/ansible/inventory/lab/hosts.yml" "$repo_root/ansible/playbooks/deploy-stack.yml"     -e stack_name=dozzle     -e homelab_release_commit="$release_commit"     -e homelab_tooling_commit="$(git rev-parse HEAD)"     -e homelab_transaction_id="$tx"     -e homelab_contract_hash="$contract_hash"     -e homelab_manifest_hash="$manifest_hash"     -e homelab_previous_accepted_commit="$prev_commit"     -e homelab_previous_record_id="$prev_id"     -e homelab_previous_record_source="$prev_source"     -e homelab_previous_release_root="$prev_root"     -e homelab_repo_root="$repo_root"     -e homelab_release_root="$release_root"
}

commit="$(git rev-parse HEAD)"
invoke "$baseline_root" retired-baseline "$commit" "" "" "" ""
sudo test -f "$target_dir/retired.txt" || { printf 'FAIL: baseline retired fixture was not deployed.\n' >&2; exit 1; }

sudo cat "$record_file" | tee "$tmp_root/previous.record" >/dev/null
previous_id="$(sha256sum "$tmp_root/previous.record" | awk '{print $1}')"

invoke "$repo_root" retired-forward "$commit" "$commit" "$previous_id" "$tmp_root/previous.record" "$baseline_root"

sudo test ! -e "$target_dir/retired.txt" || {
  printf 'FAIL: retired managed file survived successful forward convergence.\n' >&2
  exit 1
}
sudo /usr/bin/python3 "$repo_root/scripts/verify-compose-health.py"   --stack-dir "$target_dir" --compose-file docker-compose.yml --env-file defaults.env   --contract "$repo_root/stacks/dozzle/stack.yml"

printf 'Retired-file convergence proof passed.\n'
