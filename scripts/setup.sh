#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/setup.sh [--install-only] [--stack NAME]

Installs the local runtime dependencies on Debian/Ubuntu and, by default,
validates the repository and deploys the selected stack to the local Lab.

Options:
  --install-only   Install dependencies but do not validate or deploy.
  --stack NAME     Stack to deploy after setup (default: dozzle).
  -h, --help       Show this help.
EOF
}

log() {
  printf '\n==> %s\n' "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found after setup: $1"
}

install_only=0
stack="dozzle"

while (($#)); do
  case "$1" in
    --install-only)
      install_only=1
      shift
      ;;
    --stack)
      (($# >= 2)) || { usage; exit 2; }
      stack="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

[[ "$stack" =~ ^[a-z0-9][a-z0-9-]*$ ]] || fail "invalid stack name: $stack"
((EUID != 0)) || fail "run this script as a normal user; it will use sudo when needed"

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo_root"

[[ -r /etc/os-release ]] || fail "cannot determine Linux distribution"
# shellcheck disable=SC1091
. /etc/os-release

case "${ID:-}" in
  debian|ubuntu)
    docker_distro="$ID"
    ;;
  *)
    fail "automatic installation currently supports Debian and Ubuntu only (detected: ${ID:-unknown})"
    ;;
esac

[[ -n "${VERSION_CODENAME:-}" ]] || fail "VERSION_CODENAME is missing from /etc/os-release"

log "Checking sudo access"
sudo -v

if [[ "$docker_distro" == "ubuntu" ]] && ! apt-cache show ansible-core >/dev/null 2>&1; then
  log "Enabling the Ubuntu universe repository"
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install --yes software-properties-common
  sudo add-apt-repository --yes universe
fi

log "Installing base packages"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install --yes \
  ansible-core \
  ca-certificates \
  curl \
  git \
  gnupg \
  make \
  python3 \
  python3-yaml \
  sudo \
  tar \
  util-linux

add_docker_repository() {
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${docker_distro}/gpg" \
    | sudo gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  architecture="$(dpkg --print-architecture)"
  printf '%s\n' \
    "deb [arch=${architecture} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${docker_distro} ${VERSION_CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    if docker compose version >/dev/null 2>&1; then
      log "Docker Engine and Compose v2 are already installed"
      return
    fi

    log "Docker Engine is installed; adding Compose v2"
    if apt-cache show docker-compose-v2 >/dev/null 2>&1; then
      sudo DEBIAN_FRONTEND=noninteractive apt-get install --yes docker-compose-v2
    elif apt-cache show docker-compose-plugin >/dev/null 2>&1; then
      sudo DEBIAN_FRONTEND=noninteractive apt-get install --yes docker-compose-plugin
    fi

    if docker compose version >/dev/null 2>&1; then
      return
    fi

    add_docker_repository
    sudo DEBIAN_FRONTEND=noninteractive apt-get install --yes docker-compose-plugin
    docker compose version >/dev/null 2>&1 \
      || fail "Docker is installed but Compose v2 could not be added automatically"
    return
  fi

  log "Installing Docker Engine and Compose v2"
  add_docker_repository
  sudo DEBIAN_FRONTEND=noninteractive apt-get install --yes \
    containerd.io \
    docker-buildx-plugin \
    docker-ce \
    docker-ce-cli \
    docker-compose-plugin
}

install_docker

log "Starting Docker"
if command -v systemctl >/dev/null 2>&1 && [[ -d /run/systemd/system ]]; then
  sudo systemctl enable --now docker
elif command -v service >/dev/null 2>&1; then
  sudo service docker start
fi
sudo docker info >/dev/null

for command_name in ansible-inventory ansible-playbook docker git make python3; do
  require_command "$command_name"
done
docker compose version >/dev/null

if ((install_only == 1)); then
  log "Dependencies installed"
  exit 0
fi

stack_dir="$repo_root/stacks/$stack"
[[ -f "$stack_dir/stack.yml" ]] || fail "unknown stack: $stack"
[[ -f "$stack_dir/compose.yaml" ]] || fail "stack is missing compose.yaml: $stack"
[[ -f "$stack_dir/defaults.env" ]] || fail "stack is missing defaults.env: $stack"

log "Validating repository"
make validate

mapfile -t stack_metadata < <(
  python3 - "$stack_dir/stack.yml" <<'PY'
import sys
from pathlib import Path
import yaml

contract = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(contract["stack_target_dir"])
print(contract["stack_compose_dest"])
PY
)
((${#stack_metadata[@]} == 2)) || fail "could not read stack target metadata"
target_dir="${stack_metadata[0]}"
compose_dest="${stack_metadata[1]}"

log "Preparing external Docker networks for $stack"
while IFS= read -r network_name; do
  [[ -n "$network_name" ]] || continue
  if ! sudo docker network inspect "$network_name" >/dev/null 2>&1; then
    sudo docker network create "$network_name" >/dev/null
    printf 'Created Docker network: %s\n' "$network_name"
  fi
done < <(
  python3 - "$stack_dir/compose.yaml" <<'PY'
import sys
from pathlib import Path
import yaml

model = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8")) or {}
for key, value in (model.get("networks") or {}).items():
    if isinstance(value, dict) and value.get("external") is True:
        print(value.get("name") or key)
PY
)

log "Deploying $stack to the local Lab"
sudo -v
export HOMELAB_LAB_HOSTNAME
HOMELAB_LAB_HOSTNAME="$(hostname)"
bash scripts/deploy-stack.sh "$stack" --inventory lab

log "Deployment completed"
sudo docker compose \
  --env-file "$target_dir/defaults.env" \
  -f "$target_dir/$compose_dest" \
  ps
