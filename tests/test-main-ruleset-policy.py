#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / ".github" / "rulesets" / "v1-main.json"
VALIDATE = ROOT / ".github" / "workflows" / "validate.yml"
CODEQL = ROOT / ".github" / "workflows" / "codeql.yml"

policy = json.loads(POLICY.read_text(encoding="utf-8"))
if policy.get("name") != "v1 main change controls":
    raise SystemExit("ruleset name changed unexpectedly")
if policy.get("target") != "branch":
    raise SystemExit("v1 ruleset must target branches")
if policy.get("enforcement") != "active":
    raise SystemExit("v1 ruleset must be active when applied")
if policy.get("bypass_actors") != []:
    raise SystemExit("v1 ruleset must not grant bypass actors")

ref_name = policy.get("conditions", {}).get("ref_name", {})
if "~DEFAULT_BRANCH" not in ref_name.get("include", []):
    raise SystemExit("v1 ruleset must target the default branch")

rules = {rule.get("type"): rule for rule in policy.get("rules", [])}
for required in ("deletion", "non_fast_forward", "pull_request", "required_status_checks"):
    if required not in rules:
        raise SystemExit(f"v1 ruleset is missing {required!r}")

pull = rules["pull_request"].get("parameters", {})
if pull.get("required_approving_review_count") != 0:
    raise SystemExit("solo-maintainer ruleset must require zero approvals")
if pull.get("require_last_push_approval") is not False:
    raise SystemExit("solo-maintainer ruleset must not require another last-push approver")
if pull.get("require_code_owner_review") is not False:
    raise SystemExit("v1 ruleset must not require code-owner approval")

status = rules["required_status_checks"].get("parameters", {})
if status.get("strict_required_status_checks_policy") is not True:
    raise SystemExit("required checks must use strict/up-to-date semantics")

required_contexts = {
    item["context"] for item in status.get("required_status_checks", [])
}

validate_doc = yaml.safe_load(VALIDATE.read_text(encoding="utf-8"))
codeql_doc = yaml.safe_load(CODEQL.read_text(encoding="utf-8"))

validate_job_names = {
    job.get("name")
    for job in validate_doc.get("jobs", {}).values()
    if isinstance(job, dict) and job.get("name")
}
codeql_job_names = {
    job.get("name")
    for job in codeql_doc.get("jobs", {}).values()
    if isinstance(job, dict) and job.get("name")
}

expected_contexts = validate_job_names | codeql_job_names
if required_contexts != expected_contexts:
    missing = sorted(expected_contexts - required_contexts)
    extra = sorted(required_contexts - expected_contexts)
    raise SystemExit(
        f"ruleset/workflow check mismatch: missing={missing}, extra={extra}"
    )

if "OpenSSF Scorecard" in required_contexts:
    raise SystemExit("Scorecard is not a pull-request required check")

print(
    "Main ruleset policy tests passed: default-branch PR enforcement, zero "
    f"human approvals, destructive-update guards, and {len(required_contexts)} "
    "strict workflow checks."
)
