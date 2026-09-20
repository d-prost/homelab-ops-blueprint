# Main branch change controls

Issue #37 defines the v1 GitHub change-control boundary.

The desired state is one active repository branch ruleset named:

```text
v1 main change controls
```

It targets the default branch and has no bypass actors.

## Enforced rules

The ruleset requires:

- all changes to `main` to arrive through a pull request;
- zero mandatory human approvals, matching the solo-maintainer model;
- branch deletion blocked;
- force-push blocked;
- required checks to be strict, so the PR is tested against the latest base state.

The required PR checks are:

```text
Static validation
Disposable rollback proof
Disposable idempotency proof
Acceptance persistence failure proof
Stale accepted marker proof
Interruption recovery proof
SSH session interruption proof
Failure matrix runtime proof
CodeQL / Python
```

`OpenSSF Scorecard` is intentionally not a required PR check because the
Scorecard workflow is not a stable pull-request check in the current workflow
model. It remains enabled independently.

GitHub rulesets require repository Administration write permission to create or
update through the REST API.

## Apply

Use a GitHub identity with repository `Administration: write` and an
authenticated GitHub CLI:

```bash
bash scripts/configure-main-ruleset.sh
```

The script creates or updates the named ruleset from:

```text
.github/rulesets/v1-main.json
```

and then runs the verification script.

To target a fork or test repository:

```bash
HOMELAB_GITHUB_REPO=owner/repository \
  bash scripts/configure-main-ruleset.sh
```

## Verify effective enforcement

Run:

```bash
bash scripts/verify-main-ruleset.sh
```

Verification reads both the configured repository ruleset and GitHub's effective
rules for `main`. It requires GitHub to report `main` as protected.

## Blocked-merge proof

After the ruleset is active, the final acceptance proof for #37 is a temporary
pull request whose latest commit has at least one required machine check in a
failing state.

Confirm in GitHub that merge is blocked while the check is failing. Then fix or
close the temporary PR; do not bypass the ruleset.

A normal maintainer pull request with all required checks passing must remain
mergeable without an independent human approval.

Do not close #37 until both behaviors have been observed:

1. failing required check -> merge blocked;
2. all required checks green -> normal solo-maintainer merge allowed.

## Boundary

This ruleset enforces the Git review and CI acceptance path. It is not a
deployment authorization system and does not replace the runtime transaction
contract.
