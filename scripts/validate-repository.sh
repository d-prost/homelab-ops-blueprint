#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"; cd "$repo_root"
while IFS= read -r -d '' script; do bash -n "$script"; done < <(find scripts tests -type f -name '*.sh' -print0)
python3 - <<'PYCODE'
from pathlib import Path
for path in sorted(Path('scripts').glob('*.py')):
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
print('Python syntax validation passed.')
PYCODE
python3 scripts/check-public-safety.py
python3 scripts/validate-stack-contracts.py
python3 tests/test-stack-contracts.py
python3 tests/test-functional-check-parsing.py
python3 tests/test-operational-coverage.py
bash tests/test-integrity-guards.sh
if command -v yamllint >/dev/null 2>&1; then yamllint -d '{extends: default, rules: {line-length: disable, truthy: disable}}' .github ansible stacks; fi
if command -v shellcheck >/dev/null 2>&1; then find scripts tests -type f -name '*.sh' -print0 | xargs -0 shellcheck; fi
if command -v ansible-playbook >/dev/null 2>&1; then
  export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"
  HOMELAB_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/preflight.yml -e stack_name=dozzle -e homelab_repo_root="$repo_root" -e homelab_release_root="$repo_root" --syntax-check
  HOMELAB_LAB_HOSTNAME=ci-example ansible-playbook -i ansible/inventory/lab/hosts.yml ansible/playbooks/deploy-stack.yml -e stack_name=dozzle -e homelab_release_commit=1111111111111111111111111111111111111111 -e homelab_repo_root="$repo_root" -e homelab_release_root="$repo_root" --syntax-check
fi
if [[ "${HOMELAB_STRICT_VALIDATION:-0}" == "1" ]]; then command -v gitleaks >/dev/null || { echo 'ERROR: gitleaks required in strict mode' >&2; exit 1; }; gitleaks dir . --redact --no-banner --config .gitleaks.toml; fi
printf 'Validation passed.\n'
