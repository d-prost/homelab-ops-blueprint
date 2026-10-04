# Learning from Production

This repository is public and environment-neutral, but some of its strongest
safety rules come from operating real systems. Real use exposes failure modes
that are difficult to predict from a clean-room design alone.

The goal is to keep those lessons without coupling the blueprint to any private
environment.

The rule is simple:

> Promote the lesson, not the Production evidence.

A private incident, deployment, recovery drill, or failed change may reveal a
useful engineering principle. The public repository may adopt that principle
only after it has been generalized, stripped of environment-specific details,
and expressed in a way that can be tested without access to the system where it
was first observed.

## What is eligible

Good source material includes:

- merged and accepted operational changes;
- failures with a understood root cause;
- recovery drills with representative functional verification;
- rollback or cutback results;
- operating decisions backed by reproducible evidence.

Temporary or ambiguous state is not a learning source. In particular, do not
promote rules from dirty worktrees, unresolved merges, draft experiments,
one-off debugging, assumptions, or conclusions that were never verified.

An observation is useful evidence. It is not automatically a reusable rule.

## Promotion path

A Production-derived lesson should move through this sequence:

```text
private observation
        |
        v
understood root cause
        |
        v
generalized principle
        |
        v
public-safe wording
        |
        v
synthetic or repository-level proof
        |
        v
advisory rule
```

If a rule later proves stable enough to enforce, enforcement is a separate
change. It must have its own review, tests, failure semantics, and justification.

An advisory rule never becomes a deployment requirement just because it was
learned from Production.

## Public/private boundary

The public side should contain only the reusable part of the lesson. It must not
contain private hostnames, addresses, usernames, credentials, backup locations,
snapshot or run identifiers, private topology, real recovery records, or private
RPO/RTO values.

Public CI must not be given access to a private operations repository in order
to keep this registry current. Promotion is deliberately one-way and reviewed:

```text
private operations -> sanitized lesson -> public blueprint
```

The blueprint does not pull from Production, and Production does not delegate
authority to the blueprint.

## Advisory registry

Reusable lessons live in `advisory/rules.yml`.

The registry is intentionally small. A rule belongs there when:

1. the root cause is understood;
2. the lesson is useful beyond one application or host;
3. the recommendation is deterministic enough to review;
4. the behavior can be tested without private infrastructure;
5. it does not merely duplicate a stronger invariant that already exists; and
6. it can be written without publishing private evidence.

The registry is validated by `scripts/validate-advisory-rules.py`. All current
entries have `status: advisory`. Unknown fields and stronger statuses are
rejected so the registry cannot quietly grow into another policy engine.

The advisory registry is not read by `scripts/deploy-stack.sh` and has no
Production mutation authority.

## Using the rules during design and review

The rules are meant to improve engineering review. When a proposed change
matches one of them, the useful questions are:

- What state must exist before the first mutation?
- What happens if post-change acceptance fails?
- Is there one clear content authority for each managed artifact?
- Can a helper process accidentally consume the control stream that drives the
  rest of the operation?

A recommendation from this registry is still a recommendation. The operator,
the stack contract, and the transaction model keep their existing authority.

## Future tooling

A read-only change advisor may consume this registry later if that proves useful.
That tool should explain which rules are relevant and why. It should not deploy,
approve, or block Production changes by itself.

Keeping that step separate avoids expanding the v1 transaction path before the
advisory model has earned the additional complexity.
