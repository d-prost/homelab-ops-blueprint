# Recovery readiness

Configuration rollback is only part of the story for a stateful service. Before changing a Production stack with persistent data, the deployment script can require evidence that the current service can actually be restored and that rolling the configuration back would still be safe.

The check is implemented by `scripts/check-recovery-readiness.py`.

## What the check expects

For a stateful stack, the readiness file must show that:

- it applies to the current stack generation;
- it covers the complete set of stateful services;
- an isolated restore completed successfully;
- the restored service passed functional checks;
- the restore test did not modify Production;
- the environment's RPO and RTO objectives were met;
- configuration rollback to the previous deployment is compatible with the candidate;
- the result is explicitly marked `ready`;
- the backup observation is recent enough for the supplied maximum age.

The maximum backup age is supplied at deployment time because backup schedules differ between environments.

## Stack generation hash

Recovery evidence is tied to the version of the stack it was tested against. Calculate the current hash with:

```bash
python3 scripts/check-recovery-readiness.py \
  stacks/<stack>/stack.yml \
  --print-contract-hash
```

The hash includes recovery-relevant parts of the stack, including:

- the stack name;
- stateful storage, backup and restore declarations;
- expected services and functional checks;
- the managed-file contract;
- hashes of managed payload files;
- hashes of referenced restore runbooks.

Changes to those inputs produce a different hash, so older readiness evidence no longer matches automatically.

## Readiness file

The current schema is:

```json
{
  "schema_version": 1,
  "contract_hash": "<sha256 from the current stack generation>",
  "covered_services": ["example-db"],
  "disposition": "ready",
  "isolated_restore": {
    "passed": true,
    "functional_verification": true,
    "production_unchanged": true
  },
  "recovery_objectives": {
    "rpo_met": true,
    "rto_met": true
  },
  "rollback_compatibility": {
    "configuration_rollback_safe": true
  },
  "backup_receipt": {
    "observed_at": "2026-01-01T12:00:00Z"
  }
}
```

The schema is strict and unknown fields are rejected. The file contains only the values needed by the deployment check; the underlying backup and restore records can stay with the system that produced them.

`configuration_rollback_safe` is separate from restore success. A restore can work while returning to the previous application version would still be unsafe because of a schema or data-format change.

The readiness file must be a regular file outside the repository checkout and must not be group- or world-writable.

## Production use

Set the readiness file and the maximum accepted backup age before running the normal deployment command:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/path/to/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<seconds>

bash scripts/deploy-stack.sh <stack> --check
bash scripts/deploy-stack.sh <stack>
```

The same check is used for normal deployments, Production Check Mode and historical stack deployments when the selected or current stack is stateful.

If current `main` marks a stack as stateful, selecting an older release that predates the stateful declaration does not make the readiness requirement disappear.

Stateless stacks do not need a readiness file.

## Common failures

The command exits without authorizing the deployment when, for example:

- the JSON is incomplete or uses an unsupported schema version;
- the contract hash does not match the current stack generation;
- one of the stateful services is missing from `covered_services`;
- the restore or functional check is marked failed;
- `production_unchanged`, `rpo_met`, `rto_met` or `configuration_rollback_safe` is false;
- `disposition` is not `ready`;
- `backup_receipt.observed_at` is invalid, in the future or too old;
- the readiness file is missing or has unsafe local permissions.

Passing this check does not restore application data automatically. It only allows the configuration deployment to continue after the recovery prerequisites have been checked.
