#!/usr/bin/env bash
set -Eeuo pipefail

repo="${HOMELAB_GITHUB_REPO:-d-prost/homelab-ops-blueprint}"
ruleset_name="v1 main change controls"
api_version="2026-03-10"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

for command_name in gh python3 mktemp; do
  command -v "$command_name" >/dev/null 2>&1 || fail "required command not found: $command_name"
done

gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated"

tmp_root="$(mktemp -d)"
cleanup() { rm -rf -- "$tmp_root"; }
trap cleanup EXIT

rulesets_file="$tmp_root/rulesets.json"
branch_rules_file="$tmp_root/main-rules.json"
branch_file="$tmp_root/main.json"

gh api   -H 'Accept: application/vnd.github+json'   -H "X-GitHub-Api-Version: $api_version"   "/repos/$repo/rulesets?includes_parents=false" >"$rulesets_file"

ruleset_id="$(
  python3 - "$rulesets_file" "$ruleset_name" <<'PY'
import json
import sys
from pathlib import Path

items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
name = sys.argv[2]
matches = [item for item in items if item.get("name") == name]
if len(matches) != 1:
    raise SystemExit(f"ERROR: expected exactly one active repository ruleset named {name!r}, got {len(matches)}")
item = matches[0]
if item.get("enforcement") not in {"active", "enabled"}:
    raise SystemExit(f"ERROR: ruleset is not active: {item.get('enforcement')!r}")
print(item["id"])
PY
)"

gh api   -H 'Accept: application/vnd.github+json'   -H "X-GitHub-Api-Version: $api_version"   "/repos/$repo/rulesets/$ruleset_id" >"$tmp_root/ruleset.json"

gh api   -H 'Accept: application/vnd.github+json'   -H "X-GitHub-Api-Version: $api_version"   "/repos/$repo/rules/branches/main?per_page=100" >"$branch_rules_file"

gh api   -H 'Accept: application/vnd.github+json'   -H "X-GitHub-Api-Version: $api_version"   "/repos/$repo/branches/main" >"$branch_file"

python3 - "$tmp_root/ruleset.json" "$branch_rules_file" "$branch_file" <<'PY'
import json
import sys
from pathlib import Path

ruleset = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
branch_rules = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
branch = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

expected_checks = {
    "Static validation",
    "Disposable rollback proof",
    "Disposable idempotency proof",
    "Acceptance persistence failure proof",
    "Stale accepted marker proof",
    "Interruption recovery proof",
    "SSH session interruption proof",
    "Failure matrix runtime proof",
    "CodeQL / Python",
}

if ruleset.get("target") != "branch":
    raise SystemExit("ERROR: v1 ruleset does not target branches")
if ruleset.get("enforcement") not in {"active", "enabled"}:
    raise SystemExit("ERROR: v1 ruleset is not active")

conditions = ruleset.get("conditions", {}).get("ref_name", {})
if "~DEFAULT_BRANCH" not in conditions.get("include", []):
    raise SystemExit("ERROR: v1 ruleset does not target the default branch")

if ruleset.get("bypass_actors"):
    raise SystemExit("ERROR: v1 ruleset unexpectedly grants bypass actors")

rule_by_type = {rule.get("type"): rule for rule in ruleset.get("rules", [])}
for required in ("deletion", "non_fast_forward", "pull_request", "required_status_checks"):
    if required not in rule_by_type:
        raise SystemExit(f"ERROR: missing required rule: {required}")

pull = rule_by_type["pull_request"].get("parameters", {})
if pull.get("required_approving_review_count") != 0:
    raise SystemExit("ERROR: solo-maintainer ruleset must require zero human approvals")
if pull.get("require_last_push_approval") is not False:
    raise SystemExit("ERROR: last-push approval would deadlock the solo-maintainer model")
if pull.get("require_code_owner_review") is not False:
    raise SystemExit("ERROR: code-owner approval is outside the v1 maintainer model")

status = rule_by_type["required_status_checks"].get("parameters", {})
actual_checks = {item.get("context") for item in status.get("required_status_checks", [])}
if actual_checks != expected_checks:
    missing = sorted(expected_checks - actual_checks)
    extra = sorted(actual_checks - expected_checks)
    raise SystemExit(f"ERROR: required-check mismatch; missing={missing}, extra={extra}")
if status.get("strict_required_status_checks_policy") is not True:
    raise SystemExit("ERROR: required checks are not strict/up-to-date")

active_types = {rule.get("type") for rule in branch_rules}
for required in ("deletion", "non_fast_forward", "pull_request", "required_status_checks"):
    if required not in active_types:
        raise SystemExit(f"ERROR: main does not report active rule: {required}")

if branch.get("protected") is not True:
    raise SystemExit("ERROR: GitHub does not report main as protected after applying the ruleset")

print("Main change controls verified:")
print("- main is protected")
print("- pull requests are required with zero human approvals")
print("- force-push and branch deletion are blocked")
print(f"- {len(expected_checks)} machine checks are required and strict")
PY
