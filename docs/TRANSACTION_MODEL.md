# v1 Transaction Model

This document defines the normative transaction semantics targeted for `v1.0.0`.

It is an architecture contract, not a claim that every rule below is already implemented on `main`. Pre-1.0 work should converge the implementation and tests toward this contract without expanding the project into a general orchestration platform.

## v1 promise

For one authorized candidate and one verified target, the system either produces a functionally verified, durably recorded accepted configuration, or states precisely why it did not and what happened to the previous accepted configuration.

The central acceptance rule is:

```text
Git state != accepted Production state

runtime verification PASS != accepted state

runtime verification PASS
+
durable acceptance evidence
=
ACCEPTED
```

Version 1 does not promise application-data recovery, continuous reconciliation, distributed transaction coordination, or multi-host orchestration.

## Scope

The transaction model covers the path from an authorized Git-backed candidate to a verified Docker Compose configuration on one target.

It owns:

- candidate authorization and freezing;
- transport and declared-target verification;
- stack-contract and manifest validation;
- rollback-material preflight;
- bounded configuration mutation;
- functional runtime verification;
- durable acceptance evidence;
- interruption handling;
- verified configuration rollback.

It does not become a scheduler, reconciliation daemon, secrets manager, backup engine, service mesh, cluster control plane, or deployment database.

## Candidate

A candidate is the stack payload authorized for the transaction.

Before a Production mutation begins, the transaction MUST resolve the candidate to an exact Git commit:

```text
candidate_commit
```

Recording a commit SHA is not sufficient by itself. The selected stack payload MUST be materialized into an immutable transaction snapshot before the transaction reaches `PREPARED`.

After `PREPARED`, mutable `HEAD` MUST NOT redefine the candidate.

## Tooling

The deployment control logic can be newer than the selected stack payload. This is already an intentional property of historical deployments: an older stack payload must not bring back older safety logic.

The transaction therefore records a separate:

```text
tooling_commit
```

The tooling identity covers the current deployment wrappers, validation logic, Ansible roles, runtime verifier, and recovery-readiness checks.

In a normal deployment, `candidate_commit` and `tooling_commit` can be identical. In a historical deployment they can differ.

Per-script hashes are not required when `tooling_commit` fully identifies the control tooling.

## Previous accepted state

At transaction preparation time, the system MUST resolve the last durable accepted state, when one exists.

The transaction context records:

```text
previous_accepted_commit
previous_record_id
```

If no previous accepted state exists, that fact MUST be explicit.

The previous accepted state is part of the frozen transaction context. It must not be discovered for the first time only after a candidate fails.

## Transaction context

Before mutation, the transaction has a stable identity containing at least:

```text
transaction_id

candidate_commit
tooling_commit

stack

target_identity

contract_hash
manifest_hash

previous_accepted_commit
previous_record_id
```

Additional implementation fields are allowed, but they must not weaken or obscure these identities.

## Candidate freeze

Preparation follows this model:

```text
authorize repository state
        |
        v
resolve candidate_commit
        |
        v
resolve tooling_commit
        |
        v
materialize immutable candidate snapshot
        |
        v
materialize previous accepted rollback snapshot
        |
        v
calculate contract_hash
        |
        v
calculate manifest_hash
        |
        v
PREPARED
```

Once prepared, the transaction MUST NOT depend on a later interpretation of mutable branch refs to decide which candidate it is applying.

Rollback material that is required after mutation SHOULD already be materialized before the first Production mutation.

## Target identity

Target verification has two layers.

### Transport identity

Remote Production deployments MUST verify the SSH server identity through normal SSH host-key verification.

The transaction must not silently accept an unknown or replaced host key.

Transport identity answers:

> Which SSH endpoint did the control host connect to?

### Declared target identity

After connecting, the target MUST match the hostname declared by the selected inventory.

An inventory MAY additionally provide:

```text
expected_machine_id
```

When provided, it must match the target's stable machine identity.

Machine ID is optional in v1 because disposable and cloned environments do not always provide a stable identity suitable for a repository-level contract.

The baseline Production identity is therefore:

```text
verified SSH host key
+
expected hostname
```

with optional stronger binding through a declared machine identity.

The project should not describe hostname-only verification as proof of an exact physical machine identity.

## Concurrency boundary

Production mutation MUST be serialized for a target/stack pair on one configured control host.

The lock must not depend only on a user-specific `XDG_RUNTIME_DIR`, because two users or two runtime environments on the same control host must not obtain independent locks for the same Production transaction boundary.

A host-global lock location is the expected model, for example:

```text
/run/lock/homelab-ops/<target>/<stack>.lock
```

The v1 guarantee is intentionally local:

> Transactions launched through one configured control host are serialized for the same target/stack boundary.

Version 1 does not provide distributed locking across independent control hosts.

## Rollback-material preflight

Before the first mutation, an existing previous accepted state MUST be proven recoverable at the configuration level.

The preflight must prove that the transaction can obtain all required rollback material, including:

- the previous accepted record;
- the previous accepted commit identity;
- the previous stack contract;
- the previous manifest;
- the complete previous managed-file set;
- materialized previous managed payload;
- immutable runtime images required by the previous state.

The check is not satisfied merely because the previous Git commit is named in a record.

### Runtime image availability

A digest-pinned image reference proves identity, not availability.

Before mutation, the runtime images required for rollback MUST be either:

- already available on the target; or
- successfully retrievable by digest.

Where practical, immutable runtime artifacts SHOULD be prefetched before configuration mutation so a registry outage does not turn a candidate failure into an avoidable rollback failure.

The same principle SHOULD be applied to candidate runtime images.

## Pre-mutation refusal

If any required precondition fails before Production mutation, the terminal result is:

```text
PRE_MUTATION_REFUSAL
```

Examples include failure of:

- repository authorization;
- candidate freeze;
- target verification;
- stack-contract validation;
- manifest validation;
- rollback-material preflight;
- required artifact availability;
- concurrency-lock acquisition.

A pre-mutation refusal is not a failed deployment that needs rollback, because the managed Production state was not changed.

## Transaction phases

The implementation does not need a workflow engine, but its observable behavior follows these phases:

```text
PREPARED
   |
   v
MUTATING
   |
   v
VERIFYING
```

If functional verification succeeds:

```text
VERIFYING
   |
   | PASS
   v
COMMITTING_ACCEPTANCE
   |
   v
ACCEPTED
```

If functional verification fails:

```text
VERIFYING
   |
   | FAIL
   v
RESTORING
   |
   v
REVERIFYING
   |                |
   | PASS           | FAIL
   v                v
REJECTED_        REJECTED_
ROLLBACK_        ROLLBACK_
VERIFIED         FAILED
```

## Acceptance commit point

A candidate becomes `ACCEPTED` only after both conditions are true:

```text
functional verification = PASS
AND
acceptance record persisted durably
```

The accepted record SHOULD be written using atomic filesystem semantics:

```text
write temporary file
        |
        v
fsync temporary file
        |
        v
atomic rename on the same filesystem
        |
        v
fsync parent directory
        |
        v
acceptance commit complete
```

The transaction MUST NOT report `ACCEPTED` before durable acceptance evidence has been committed.

## Acceptance persistence failure

If runtime verification succeeds but durable acceptance persistence fails, the candidate is not accepted.

The terminal result is:

```text
ACCEPTANCE_PERSISTENCE_FAILED
```

This failure MUST be fail-closed.

Automatic rollback is not required and should not be the default for this specific failure class, because an inability to persist evidence can indicate a wider host problem such as disk exhaustion, filesystem failure, permission failure, or a broken mount. Automatically writing another configuration in that condition can increase ambiguity.

Required behavior:

- the candidate is not marked accepted;
- the target state is treated as unresolved;
- new Production transactions are blocked until operator reconciliation;
- the system must not invent a stable `VERIFIED_BUT_NOT_RECORDED` accepted state.

## In-flight transaction marker

Before mutation begins, the control path SHOULD persist a minimal in-flight marker.

This is not a transaction journal and does not support resume semantics. It only proves that a transaction may have crossed the mutation boundary.

A minimal marker can identify:

```text
transaction_id
stack
candidate_commit
previous_record_id
mutation_started
```

The marker is cleared after a durable acceptance commit or after a verified rollback outcome.

If acceptance was durably committed but the process crashed before clearing the marker, the next invocation may verify that the marker's `transaction_id` matches the accepted record and then remove the stale marker.

## Interruption semantics

If a process disappears before mutation can have started, cleanup is sufficient and rollback is unnecessary.

If mutation has started, or the system cannot prove that it did not start, the target enters:

```text
INTERRUPTED_UNRESOLVED
```

No new candidate may begin until the unresolved transaction has been reconciled.

The reconciliation model is deliberately simple:

```text
detect unfinished transaction
        |
        v
read last durable ACCEPTED state
        |
        v
prove/use frozen rollback material
        |
        v
restore previous accepted managed configuration
        |
        v
functional re-verification
        |
        v
only then allow a new candidate
```

The system does not need to infer whether an interrupted candidate reached 20%, 70%, or 95% of its mutation sequence.

The rule is:

> If mutation may have started and acceptance was not durably committed, re-establish the previous accepted state before starting another transaction.

`ACCEPTANCE_PERSISTENCE_FAILED` remains operator-reconciled rather than automatically restored until the underlying persistence failure is addressed or the operator chooses an explicit recovery action.

## Verified rollback

Rollback is verified only when all of the following succeed:

- the exact previous managed configuration is restored;
- candidate-only managed files are removed;
- the previous Compose model is reapplied;
- the previous functional checks pass.

Only then is the terminal result:

```text
REJECTED_ROLLBACK_VERIFIED
```

If any required rollback or re-verification step fails:

```text
REJECTED_ROLLBACK_FAILED
```

The system must not claim that Production is healthy merely because previous files were copied back.

## Deployment record boundary

The deployment record is acceptance evidence and rollback provenance. It is not desired state and not a reconciliation database.

It may be used to:

- describe what was accepted;
- identify the exact previous accepted state;
- reconstruct rollback provenance;
- support human-invoked inspection.

A user-invoked deployment transaction may consume the last accepted record only to identify and prove the previous accepted state required for rollback.

The record MUST NOT be used to decide that a new deployment can be skipped.

Examples of prohibited semantics include:

```text
current commit == accepted commit
=> skip deployment

record says previous verification passed
=> skip current runtime verification

record changed
=> automatically redeploy

drift detected
=> automatically reconcile
```

The project does not add a record watcher, background reconciler, scheduler, central state database, or remote control API as part of v1.

## Historical evidence versus current state

Acceptance evidence describes what was proven at a specific time. It does not prove that the target remains healthy indefinitely.

Inspection output should distinguish these concepts explicitly:

```text
Last accepted commit: abc123
Last accepted verification: PASS
Verified at: 2026-09-19T...
Current runtime: NOT CHECKED
```

A future user-invoked live check may perform current functional verification, but it must not mutate or reconcile Production automatically.

## Idempotency

Idempotency is a separate v1 proof property.

The implementation should prove:

```text
accepted candidate
        |
        v
same candidate deployed again
        |
        v
managed configuration changes = 0
        |
        v
functional verification = PASS
```

A successful deployment alone does not prove stable convergence.

## Git-history independence after preparation

After `PREPARED`, rollback MUST NOT depend on future availability of:

- `origin`;
- branch reachability;
- tag reachability;
- a newly resolved Git reference.

Required previous material should already be frozen or materialized for the transaction.

Before preparation, missing or unusable previous Git material causes `PRE_MUTATION_REFUSAL`.

After preparation, the transaction uses its frozen rollback material. It must never silently substitute a different reachable revision.

## Recovery-readiness boundary

Recovery readiness in v1 is an external deployment precondition, not a backup implementation owned by the project.

The project may validate a narrow evidence projection covering facts such as:

- applicability to the current stack generation;
- covered stateful services;
- freshness;
- isolated restore result;
- functional restore verification;
- RPO/RTO assertions;
- configuration-rollback compatibility.

The project does not become responsible for implementing PostgreSQL dumps, Restic repositories, S3 retention, filesystem snapshots, or application-data restore orchestration.

A later stateful reference proof demonstrates the evidence contract. It does not create a generic backup framework.

## Terminal outcomes

The v1 transaction model keeps terminal results small and explicit:

```text
PRE_MUTATION_REFUSAL

ACCEPTED

REJECTED_ROLLBACK_VERIFIED

REJECTED_ROLLBACK_FAILED

INTERRUPTED_UNRESOLVED

ACCEPTANCE_PERSISTENCE_FAILED
```

There is no stable success state such as:

```text
PARTIALLY_ACCEPTED
VERIFIED_BUT_NOT_RECORDED
AUTO_RECOVERED_MAYBE
```

Ambiguous state is unresolved state, not weakened success.

## v1 proof work

Before `v1.0.0`, implementation work should prove this contract rather than add platform breadth.

The proof matrix includes:

1. candidate freeze and transaction identity;
2. separate candidate and tooling identities;
3. SSH transport identity verification;
4. declared target hostname verification;
5. optional machine-ID hardening;
6. rollback-material preflight;
7. candidate and rollback image availability;
8. a real remote SSH deployment proof;
9. wrong-target refusal before mutation;
10. invalid-contract refusal before mutation;
11. invalid-manifest refusal before mutation;
12. mutable-image refusal before mutation;
13. functional-verification failure and verified rollback;
14. candidate-only managed-file cleanup;
15. retired managed-file convergence;
16. host-global concurrency-lock proof, including separate user/runtime contexts;
17. idempotency proof;
18. interruption during mutation;
19. remote-connection interruption;
20. acceptance-record persistence failure;
21. rollback verification failure;
22. missing or unusable rollback artifacts;
23. registry/image-unavailability refusal before mutation;
24. an external clean-host or remote-target evaluation;
25. enforced GitHub `main` change controls appropriate for the maintainer model.

No multi-host orchestration, resume engine, dashboard, database, drift daemon, generic recovery framework, plugin system, or scheduler is required to complete this contract.

## v1 release boundary

`v1.0.0` means:

> A stable single-target transaction model for guarded Docker Compose configuration changes, with frozen provenance, verified target selection, pre-proven rollback material, functional runtime verification, durable acceptance evidence, explicit interruption semantics, and verified configuration rollback.

It explicitly does not provide application-data recovery, continuous drift reconciliation, distributed transaction coordination, or multi-host orchestration.
