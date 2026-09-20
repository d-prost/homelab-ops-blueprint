#!/usr/bin/env bash
set -Eeuo pipefail
[[ "${HOMELAB_LAB_ROLLBACK_TEST:-0}" == "1" ]] || { printf 'ERROR: set HOMELAB_LAB_ROLLBACK_TEST=1.\n' >&2; exit 1; }
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"; cd "$repo_root"
actual_hostname="$(hostname)"; export HOMELAB_LAB_HOSTNAME="$actual_hostname"
target_dir="/opt/homelab-ops/stacks/dozzle"; record_file="/etc/homelab-ops/deployments/dozzle.record"; receipt_file="/etc/homelab-ops/deployments/dozzle.receipt"; marker_file="/var/lib/homelab-ops/transactions/dozzle.unresolved"; tmp_root="$(mktemp -d)"; runtime_dir="$tmp_root/runtime"; failure_log="$tmp_root/failed-deploy.log"
[[ ! -e "$target_dir" ]] || { printf 'ERROR: disposable Lab target already exists: %s\n' "$target_dir" >&2; exit 1; }
cleanup(){ set +e; if [[ -f "$target_dir/docker-compose.yml" && -f "$target_dir/defaults.env" ]]; then sudo /usr/bin/docker compose --env-file "$target_dir/defaults.env" -f "$target_dir/docker-compose.yml" down --remove-orphans >/dev/null 2>&1; fi; sudo rm -rf -- "$target_dir"; sudo rm -f -- "$record_file" "$receipt_file" "$marker_file"; rm -rf -- "$tmp_root"; }; trap cleanup EXIT
mkdir -p "$runtime_dir"; chmod 0700 "$runtime_dir"
export XDG_RUNTIME_DIR="$runtime_dir"; export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"
bash scripts/deploy-stack.sh dozzle --inventory lab
before_compose="$(sudo sha256sum "$target_dir/docker-compose.yml" | awk '{print $1}')"; before_defaults="$(sudo sha256sum "$target_dir/defaults.env" | awk '{print $1}')"
git archive HEAD | tar -x -C "$tmp_root"
python3 - "$tmp_root/stacks/dozzle" <<'PY_INNER'
from pathlib import Path
import sys, yaml

stack = Path(sys.argv[1])
compose_path = stack / "compose.yaml"
model = yaml.safe_load(compose_path.read_text())
model["services"]["dozzle"]["entrypoint"] = ["/bin/sh", "-c", "exit 42"]
compose_path.write_text(yaml.safe_dump(model, sort_keys=False))

candidate_only = stack / "candidate-only.txt"
candidate_only.write_text("must disappear during rollback\n", encoding="utf-8")

contract_path = stack / "stack.yml"
contract = yaml.safe_load(contract_path.read_text())
contract["stack_managed_files"].append(
    {"src": "candidate-only.txt", "dest": "candidate-only.txt", "mode": "0640"}
)
contract_path.write_text(yaml.safe_dump(contract, sort_keys=False))

with (stack / "MANIFEST.tsv").open("a", encoding="utf-8") as handle:
    handle.write(
        "candidate-only.txt\t"
        f"{contract['stack_target_dir']}/candidate-only.txt\n"
    )
PY_INNER
set +e
previous_commit="$(git rev-parse HEAD)"
sudo cat "$record_file" | tee "$tmp_root/previous.record" >/dev/null
previous_record_id="$(sha256sum "$tmp_root/previous.record" | awk '{print $1}')"
contract_hash="$(sha256sum "$tmp_root/stacks/dozzle/stack.yml" | awk '{print $1}')"
manifest_hash="$(sha256sum "$tmp_root/stacks/dozzle/MANIFEST.tsv" | awk '{print $1}')"
ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg" ansible-playbook -i "$repo_root/ansible/inventory/lab/hosts.yml" "$repo_root/ansible/playbooks/deploy-stack.yml" -e stack_name=dozzle -e homelab_release_commit=1111111111111111111111111111111111111111 -e homelab_tooling_commit="$previous_commit" -e homelab_transaction_id=lab-failure-test -e homelab_contract_hash="$contract_hash" -e homelab_manifest_hash="$manifest_hash" -e homelab_previous_accepted_commit="$previous_commit" -e homelab_previous_record_id="$previous_record_id" -e homelab_previous_record_source="$tmp_root/previous.record" -e homelab_previous_release_root="$repo_root" -e homelab_repo_root="$repo_root" -e homelab_release_root="$tmp_root" >"$failure_log" 2>&1
failed_rc=$?; set -e
((failed_rc != 0)) || { cat "$failure_log" >&2; exit 1; }
grep -Fq 'REJECTED_ROLLBACK_VERIFIED' "$failure_log" || { cat "$failure_log" >&2; exit 1; }
grep -q 'prior managed files were restored' "$failure_log" || { cat "$failure_log" >&2; exit 1; }
sudo test ! -e "$target_dir/candidate-only.txt" || {
  printf 'FAIL: candidate-only managed file survived verified rollback.\n' >&2
  cat "$failure_log" >&2
  exit 1
}
after_compose="$(sudo sha256sum "$target_dir/docker-compose.yml" | awk '{print $1}')"; after_defaults="$(sudo sha256sum "$target_dir/defaults.env" | awk '{print $1}')"
[[ "$before_compose" == "$after_compose" ]]; [[ "$before_defaults" == "$after_defaults" ]]
sudo /usr/bin/python3 "$repo_root/scripts/verify-compose-health.py" --stack-dir "$target_dir" --compose-file docker-compose.yml --env-file defaults.env --contract "$repo_root/stacks/dozzle/stack.yml"
printf 'Ephemeral Lab rollback proof passed.\n'
