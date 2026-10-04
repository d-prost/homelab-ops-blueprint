# Main branch change controls

Issue #37 tracks the v1 GitHub change-control boundary for `main`.

The desired state is one active repository ruleset named:

```text
v1 main change controls
```

It targets the default branch and has no bypass actors.

## Rules

The ruleset requires:

- pull requests for changes to `main`;
- zero mandatory human approvals for the solo-maintainer model;
- force-push protection;
- branch-deletion protection;
- strict required checks against the latest base state.

Required checks:

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

OpenSSF Scorecard remains enabled independently instead of being used as a required PR gate.

## Applying the ruleset

```bash
bash scripts/configure-main-ruleset.sh
```

Policy source:

```text
.github/rulesets/v1-main.json
```

Alternate repository target:

```bash
HOMELAB_GITHUB_REPO=owner/repository \
  bash scripts/configure-main-ruleset.sh
```

## Verification

```bash
bash scripts/verify-main-ruleset.sh
```

Issue #37 is complete only after both behaviors are observed:

1. a failing required check blocks merge;
2. an all-green PR remains mergeable with zero human approvals.

## Boundary

The ruleset protects the Git review and CI path. It is not Production deployment authorization and does not replace the runtime transaction contract.
