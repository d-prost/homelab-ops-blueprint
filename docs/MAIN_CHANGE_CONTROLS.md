# Main branch change controls

Issue #37 defines the v1 GitHub change-control boundary I want on `main`.

My desired state is one active repository ruleset named:

```text
v1 main change controls
```

It targets the default branch and has no bypass actors.

## Rules I enforce

The ruleset keeps these properties:

- changes to `main` arrive through pull requests;
- zero mandatory human approvals fit my solo-maintainer model;
- branch deletion is blocked;
- force-push is blocked;
- required checks are strict against the latest base state.

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

I keep OpenSSF Scorecard enabled independently rather than making it a required PR check because its workflow is not a stable pull-request gate in the current model.

## Applying the ruleset

I apply the repository policy with a GitHub identity that has `Administration: write`:

```bash
bash scripts/configure-main-ruleset.sh
```

The source policy is:

```text
.github/rulesets/v1-main.json
```

For a fork or test repository I can override the target:

```bash
HOMELAB_GITHUB_REPO=owner/repository \
  bash scripts/configure-main-ruleset.sh
```

## Effective enforcement

My verification command is:

```bash
bash scripts/verify-main-ruleset.sh
```

I only consider #37 complete when GitHub reports effective `main` protection and I have observed both behaviors:

1. a failing required check blocks merge;
2. an all-green PR remains mergeable with zero human approvals.

## Boundary

This ruleset protects the Git review and CI acceptance path. I do not treat it as Production deployment authorization, and it does not replace the runtime transaction contract.
