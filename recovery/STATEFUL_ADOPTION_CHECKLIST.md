# Stateful service adoption checklist

Configuration rollback and application-data recovery are separate controls. A rendered Compose model or a running container is not enough to call a stateful stack ready for managed Production deployment.

## Boundaries

Before adoption, record:

- sanitized configuration managed by Git;
- persistent paths, volumes, databases, indexes, uploads and media;
- secrets kept outside Git;
- database-aware export method where applicable;
- snapshot or backup class;
- functional recovery checks using representative data;
- target and measured RPO/RTO;
- configuration rollback rule;
- explicit non-rollback rule for persistent application data;
- compatibility between the previous accepted application generation and candidate data/schema changes.

Every backup input is either **required** or **optional**. Missing required inputs fail before snapshot/export creation. Optional inputs are explicit and reported as skipped.

## Required proof

Before a stateful service moves from observed to managed:

1. remote images are pinned by digest;
2. secrets and generated runtime state stay outside the Git payload;
3. `stack.yml` and `MANIFEST.tsv` describe the same boundary;
4. a database-aware export exists when the application uses a database;
5. isolated restore succeeds with Production unchanged;
6. authentication and representative data access work after restore;
7. backup source, restore target, result and measured RPO/RTO are recorded privately;
8. applicable RPO and RTO objectives are met;
9. configuration rollback to the previous accepted generation remains safe;
10. the exact stack-generation hash is recorded;
11. the private readiness projection matches the exact stateful service set;
12. backup freshness is derived from the real cadence plus bounded margin;
13. readiness JSON stays outside the public repository and is not group- or world-writable;
14. Check Mode and one bounded real deployment use the same guarded Production path.

Generation hash:

```bash
python3 scripts/check-recovery-readiness.py \
  stacks/<stack>/stack.yml \
  --print-contract-hash
```

## Ongoing rule

Repeat the restore proof after material changes to storage layout, database engine, image generation, managed application configuration, backup writer, encryption, secret boundary or restore procedure.

A green timer, successful snapshot, monitoring presence or `container=running` is not recovery evidence.

Routine updates and historical deployments do not bypass the readiness gate.
