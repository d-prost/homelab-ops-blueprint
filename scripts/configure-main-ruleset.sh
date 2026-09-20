#!/usr/bin/env bash
set -Eeuo pipefail

repo="${HOMELAB_GITHUB_REPO:-d-prost/homelab-ops-blueprint}"
ruleset_name="v1 main change controls"
api_version="2026-03-10"

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
policy_file="$repo_root/.github/rulesets/v1-main.json"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

for command_name in gh python3 mktemp; do
  command -v "$command_name" >/dev/null 2>&1 || fail "required command not found: $command_name"
done

[[ -f "$policy_file" ]] || fail "ruleset policy not found: $policy_file"

gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated"

tmp_root="$(mktemp -d)"
cleanup() { rm -rf -- "$tmp_root"; }
trap cleanup EXIT

list_file="$tmp_root/rulesets.json"
gh api   -H 'Accept: application/vnd.github+json'   -H "X-GitHub-Api-Version: $api_version"   "/repos/$repo/rulesets?includes_parents=false" >"$list_file"

ruleset_id="$(
  python3 - "$list_file" "$ruleset_name" <<'PY'
import json
import sys
from pathlib import Path

items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
name = sys.argv[2]
matches = [item for item in items if item.get("name") == name]
if len(matches) > 1:
    raise SystemExit(f"ERROR: found {len(matches)} rulesets named {name!r}")
if matches:
    print(matches[0]["id"])
PY
)"

if [[ -n "$ruleset_id" ]]; then
  printf 'Updating repository ruleset %s (id=%s) on %s\n' "$ruleset_name" "$ruleset_id" "$repo"
  gh api     --method PUT     -H 'Accept: application/vnd.github+json'     -H "X-GitHub-Api-Version: $api_version"     "/repos/$repo/rulesets/$ruleset_id"     --input "$policy_file" >/dev/null
else
  printf 'Creating repository ruleset %s on %s\n' "$ruleset_name" "$repo"
  gh api     --method POST     -H 'Accept: application/vnd.github+json'     -H "X-GitHub-Api-Version: $api_version"     "/repos/$repo/rulesets"     --input "$policy_file" >/dev/null
fi

bash "$repo_root/scripts/verify-main-ruleset.sh"
