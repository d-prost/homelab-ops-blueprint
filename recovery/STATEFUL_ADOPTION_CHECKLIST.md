# Stateful service adoption checklist

I treat configuration rollback and application-data recovery as separate controls. A rendered Compose model or running container is not enough for me to call a stateful stack ready for managed Production deployment.

## Boundaries I define

Before adoption I record:

- sanitized configuration that Git may manage;
- persistent data paths, volumes, databases, indexes, uploads and media;
- secrets that stay outside Git;
- database-aware export method where applicable;
- filesystem snapshot or backup class;
- functional recovery checks using representative data;
- target and measured RPO/RTO;
- configuration rollback rule;
- explicit non-rollback rule for persistent application data;
- compatibility between the previous accepted application generation and candidate data/schema changes.

Every backup input is classified as **required** or **optional**. A missing required input fails before snapshot or export creation. Optional inputs are explicit and reported as skipped.

## Proof I require

Before I move a stateful service from observed to managed, I require evidence that:

1. every remote image is pinned by digest;
2. secrets and generated runtime state are outside the Git payload;
3. `stack.yml` and `MANIFEST.tsv` describe the same boundary;
4. database-aware export exists when the application uses a database;
5. isolated restore succeeds with Production unchanged;
6. authentication and representative data access work after restore;
7. backup source, restore target, result and measured RPO/RTO are recorded privately;
8. applicable RPO and RTO objectives are met;
9. configuration rollback to the previous accepted generation remains safe after candidate failure;
10. the exact public stack-generation hash is recorded;
11. the private readiness projection matches the exact stateful service set;
12. backup freshness is derived from the real cadence plus bounded operational margin;
13. readiness JSON stays outside the public repository and is not group- or world-writable;
14. Check Mode and one bounded real deployment use the same guarded Production path.

The generation hash command is:

```bash
python3 scripts/check-recovery-readiness.py \
  stacks/<stack>/stack.yml \
  --print-contract-hash
```

## Ongoing rule

I repeat the restore proof after material changes to storage layout, database engine, image generation, managed application configuration, backup writer, encryption, secret boundary or restore procedure.

A green timer, successful snapshot, monitoring presence or `container=running` is not recovery evidence.

I do not add routine-update or historical-deployment bypasses around the readiness gate.
