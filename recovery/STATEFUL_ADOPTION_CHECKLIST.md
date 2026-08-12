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
- rollback rule for configuration and the explicit rule that persistent data is never rolled back automatically.

Classify every backup input as either **required** or **optional**. A missing required path must fail before creating a snapshot. Optional paths must be explicitly declared and reported as skipped. Resolve dynamic staging paths before validation; never validate a literal variable expression as though it were a filesystem path.

## Required proof

Before changing a stateful service from observed to managed:

1. pin every remote image by digest;
2. remove secrets and generated Runtime state from the Git payload;
3. validate `stack.yml` against `MANIFEST.tsv`;
4. create a database-aware export when the application uses a database;
5. complete an isolated restore from the real backup path;
6. verify authentication plus representative record, file, media, or search access;
7. record the backup source, restore target, result, and measured RPO/RTO without publishing private evidence;
8. run a check-mode deployment followed by one bounded real deployment.

## Ongoing rule

Repeat the restore proof after a material change to the storage layout, database engine, backup writer, encryption, or secret boundary. A green timer, successful snapshot creation, or `container=running` is not recovery evidence.
