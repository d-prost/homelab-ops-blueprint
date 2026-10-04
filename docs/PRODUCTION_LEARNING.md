# Learning from Production

Some of the strongest rules in this repository come from operating real systems rather than from clean-room design.

I keep that experience useful without coupling the public blueprint to my private environment.

My rule is:

> I promote the lesson, not the Production evidence.

## What I promote

I consider a Production-derived lesson eligible when it comes from evidence such as:

- a merged and accepted operational change;
- a failure with an understood root cause;
- a representative recovery drill;
- a rollback or cutback result;
- an operating decision backed by reproducible evidence.

I do not promote rules from dirty worktrees, unresolved merges, draft experiments, one-off debugging, assumptions or conclusions that were never verified.

An observation is evidence. It is not automatically a reusable rule.

## Promotion path

My promotion path is:

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

I treat enforcement as a separate change. A rule does not become a deployment requirement merely because it was learned from Production.

## Public/private boundary

I promote mechanism, invariant, failure semantics and proof method.

I keep these details private:

- hostnames and addresses;
- usernames and credentials;
- backup locations;
- snapshot and run identifiers;
- private topology;
- real recovery records;
- private RPO/RTO values.

The direction is deliberately one-way:

```text
private operations -> sanitized lesson -> public blueprint
```

Public CI does not pull from my private operations repository, and the blueprint has no Production authority.

## Advisory registry

Reusable lessons live in `advisory/rules.yml`.

I add a rule when:

1. I understand the root cause;
2. the lesson applies beyond one application or host;
3. the recommendation is deterministic enough to review;
4. the behavior can be tested without private infrastructure;
5. it does not duplicate a stronger invariant;
6. the wording is public-safe.

`scripts/validate-advisory-rules.py` keeps the registry schema narrow. Current entries remain `status: advisory`, and stronger enforcement requires an independent mechanism and review.

The advisory registry is not consumed by `scripts/deploy-stack.sh`.

## Review use

I use the registry to ask questions such as:

- What state must exist before the first mutation?
- What happens when post-change acceptance fails?
- Is there one content authority for each managed artifact?
- Can a helper process accidentally consume the control stream?

The output is advice. The transaction contract and my explicit Production decision remain authoritative.

## Future tooling

A later read-only advisor may consume the registry and explain which rules are relevant to a proposed change.

I will keep that tool non-mutating and non-authoritative: no deploy, no approval, no hidden policy promotion and no private Production access.
