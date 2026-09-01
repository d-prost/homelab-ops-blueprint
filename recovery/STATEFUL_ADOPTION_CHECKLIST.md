# Stateful Service Adoption Checklist

Configuration rollback and data recovery are separate controls. A stack is not ready for managed Production deployment merely because its Compose model renders or its containers start.

## Define the boundaries

Document these items before adoption:

- sanitized configuration files that Git may manage;
- persistent data paths, named volumes, databases, indexes, uploads, and media;
- secret files and credentials that remain outside Git;
- database-aware export method, where applicable;
- filesystem snapshot or backup class;
- functional recovery checks using representative data;
- target and measured RPO/RTO;
- rollback rule for configuration and the explicit rule that persistent data is never rolled back automatically;
- whether the previously accepted image/configuration generation remains compatible with data or schema changes made by the candidate.

Classify every backup input as either **required** or **optional**. A missing required path must fail before creating a snapshot. Optional paths must be explicitly declared and reported as skipped. Resolve dynamic staging paths before validation; never validate a literal variable expression as though it were a filesystem path.

## Required proof

Before changing a stateful service from observed to managed:

1. pin every remote image by digest;
2. remove secrets and generated Runtime state from the Git payload;
3. validate `stack.yml` against `MANIFEST.tsv`;
4. create a database-aware export when the application uses a database;
5. complete an isolated restore from the real backup path with Production unchanged;
6. verify authentication plus representative record, file, media, or search access;
7. record the backup source, restore target, result, and measured RPO/RTO without publishing private evidence;
8. confirm the applicable RPO and RTO objectives were met;
9. confirm configuration rollback to the previously accepted generation is safe after candidate failure; schema-sensitive or migration-heavy changes that cannot prove this are not eligible for the guarded stateful path;
10. generate the exact public stack-generation hash with `scripts/check-recovery-readiness.py --print-contract-hash`;
11. create the strict private readiness projection described in `docs/RECOVERY_READINESS.md`, covering the exact stateful service set and using `ready` only when all readiness assertions are true;
12. derive the backup-freshness limit from the real backup cadence plus a bounded operational margin; for multiple required inputs, project the oldest applicable backup observation;
13. keep the readiness JSON outside the public repository tree and ensure it is not group- or world-writable;
14. run a check-mode deployment followed by one bounded real deployment through the same guarded Production path.

## Ongoing rule

Repeat the restore proof after a material change to the storage layout, database engine, container image generation, managed application configuration, backup writer, encryption, secret boundary, or restore procedure. The public generation hash intentionally invalidates readiness after managed payload or restore-runbook changes.

A green timer, successful snapshot creation, monitoring presence, or `container=running` is not recovery evidence. Do not introduce a routine-update or historical-deployment bypass around the readiness gate.
