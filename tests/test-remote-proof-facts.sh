#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp_root="$(mktemp -d)"
trap 'rm -rf -- "$tmp_root"' EXIT
mkdir -p "$tmp_root/bin"
printf '%s\n' 'all: {}' > "$tmp_root/hosts.yml"

cat > "$tmp_root/bin/ansible-inventory" <<'MOCK'
#!/usr/bin/env bash
printf '%s\n' '{"_meta":{"hostvars":{"synthetic-target":{"ansible_connection":"ssh","homelab_environment":"lab","homelab_expected_hostname":"synthetic-target"}}}}'
MOCK

cat > "$tmp_root/bin/ansible-playbook" <<'MOCK'
#!/usr/bin/env bash
if [[ "${1:-}" == "--version" ]]; then
  printf '%s\n' 'ansible-playbook [core 2.20.1]'
fi
MOCK

cat > "$tmp_root/bin/ansible" <<'MOCK'
#!/usr/bin/env bash
if [[ "${ANSIBLE_MOCK_FAIL:-0}" == "1" ]]; then
  printf '%s\n' 'synthetic-target | FAILED! => private diagnostic' >&2
  exit 1
fi
case "$*" in
  *'docker version --format'*)
    [[ "$*" == *'{% raw %}{{.Server.Version}}{% endraw %}'* ]] || exit 2
    printf '%s\n' 'synthetic-target | SUCCESS | rc=0 | (stdout) 29.8.1'
    ;;
  *'docker compose version --short'*)
    printf '%s\n' 'synthetic-target | SUCCESS | rc=0 | (stdout) 5.5.1'
    ;;
  *)
    printf '%s\n' 'synthetic-target | CHANGED | rc=0 | (stdout) Ubuntu 26.04'
    ;;
esac
MOCK

chmod +x "$tmp_root/bin/"*

output="$(PATH="$tmp_root/bin:$PATH" HOMELAB_REMOTE_PROOF=1 \
  bash "$repo_root/scripts/collect-remote-proof-facts.sh" "$tmp_root/hosts.yml")"
grep -Fq 'Inventory policy: PASS' <<<"$output"
grep -Fq 'Control Ansible: ansible-playbook [core 2.20.1]' <<<"$output"
grep -Fq 'Target OS: Ubuntu 26.04' <<<"$output"
grep -Fq 'Docker Engine: 29.8.1' <<<"$output"
grep -Fq 'Docker Compose: 5.5.1' <<<"$output"
if grep -Fq 'synthetic-target |' <<<"$output"; then
  printf 'FAIL: private target alias escaped the public fact report.\n' >&2
  exit 1
fi

set +e
failed_output="$(PATH="$tmp_root/bin:$PATH" HOMELAB_REMOTE_PROOF=1 \
  ANSIBLE_MOCK_FAIL=1 bash "$repo_root/scripts/collect-remote-proof-facts.sh" \
  "$tmp_root/hosts.yml" 2>&1)"
failed_rc=$?
set -e
((failed_rc != 0))
grep -Fq 'fact query failed' <<<"$failed_output"
if grep -Fq 'private diagnostic' <<<"$failed_output"; then
  printf 'FAIL: private diagnostic escaped the failed fact report.\n' >&2
  exit 1
fi

printf 'Remote proof fact collection tests passed.\n'
