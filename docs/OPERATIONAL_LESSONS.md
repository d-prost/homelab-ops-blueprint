# Operational lessons

Real operations expose failure modes that are difficult to predict from design alone. Reusable lessons can be carried into the public blueprint without copying private Production evidence.

The boundary is simple:

> Generalize the lesson, keep the evidence private.

## Eligible lessons

Useful source material includes:

- accepted operational changes;
- failures with an understood root cause;
- representative recovery drills;
- rollback or cutback results;
- decisions backed by reproducible evidence.

Dirty worktrees, unresolved merges, draft experiments, one-off debugging and unverified assumptions are not suitable sources for reusable rules.

## Promotion path

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

Advisory rules do not become deployment requirements automatically. Enforcement is a separate reviewed change.

## Public/private boundary

Public content can describe mechanisms, invariants, failure semantics and proof methods.

Private material includes:

- hostnames and addresses;
- usernames and credentials;
- backup locations;
- snapshot and run identifiers;
- private topology;
- real recovery records;
- private RPO/RTO values.

The direction remains one-way:

```text
private operations -> generalized lesson -> public blueprint
```

Public CI does not need access to private operations data.

## Advisory registry

Reusable rules live in `advisory/rules.yml`.

A rule belongs there when the root cause is understood, the lesson applies beyond one host/application, the recommendation is deterministic enough to review, and the behavior can be tested without private infrastructure.

`scripts/validate-advisory-rules.py` keeps the registry schema narrow. Current entries remain `status: advisory`.

The registry is not consumed by `scripts/deploy-stack.sh`.

## Review use

Typical review questions include:

- What state must exist before the first mutation?
- What happens when post-change acceptance fails?
- Is there one content authority for each managed artifact?
- Can a subprocess consume a control stream it does not need?

Any future tooling around these rules should remain read-only and non-authoritative.
