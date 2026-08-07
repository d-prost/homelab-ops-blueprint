#!/usr/bin/env bash
set -Eeuo pipefail

if (($# != 1)); then
  printf 'Usage: %s INVENTORY_FILE\n' "$0" >&2
  exit 2
fi
inventory_file="$1"
[[ -r "$inventory_file" ]] || { printf 'ERROR: inventory is not readable: %s\n' "$inventory_file" >&2; exit 1; }
inventory_json="$(ansible-inventory -i "$inventory_file" --list)"
host_count="$(python3 -c '
import json, sys
obj=json.load(sys.stdin)
print(len(obj.get("_meta", {}).get("hostvars", {})))
' <<<"$inventory_json")"
[[ "$host_count" =~ ^[0-9]+$ ]] || exit 1
((host_count > 0)) || { printf 'ERROR: inventory resolves to zero hosts: %s\n' "$inventory_file" >&2; exit 1; }
printf 'Inventory host guard passed: %s host(s)\n' "$host_count"
