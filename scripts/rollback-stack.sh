#!/usr/bin/env bash
set -Eeuo pipefail
if (($# != 2)); then printf 'Usage: %s STACK RELEASE_TAG\n' "$0" >&2; exit 2; fi
[[ "$2" =~ ^release-[0-9]{8}-[0-9]{6}Z$ ]] || { printf 'ERROR: invalid release tag.\n' >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec "$script_dir/deploy-stack.sh" "$1" --ref "$2"
