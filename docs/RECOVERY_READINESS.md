# Recovery Readiness Gate

Stateful deployment safety requires a separate recovery decision. A valid Compose model, a successful configuration rollback path, or the existence of a backup does not prove that application data is currently recoverable.

The public blueprint therefore defines a **consumer-side readiness gate**. It does not write backups, store credentials, know private repository locations, or publish real restore evidence.

## Decision model

For a stateful stack, Production readiness is accepted only when all of these are true:

1. the public `operations:` contract declares the state boundary;
2. private evidence is bound to the current recovery-relevant contract hash;
3. an isolated restore passed;
4. the restored service passed a functional verification, not only a container or file-existence check;
5. the private evidence has an explicit `ready` disposition;
6. backup evidence is fresh enough for an environment-supplied policy.

The freshness policy is intentionally not embedded in this repository. A real environment derives it from its backup cadence plus an operational margin and passes the resulting maximum age to the gate.

## Contract binding

The gate hashes only recovery-relevant declarations from stateful services:

- `persistent_mounts`;
- `backup`;
- `restore`.

A change to those declarations changes the hash and invalidates older evidence automatically. Monitoring-only changes do not invalidate an otherwise applicable restore proof.

Generate the current hash with:

```bash
python3 scripts/check-recovery-readiness.py stacks/<stack>/stack.yml --print-contract-hash
```

## Private evidence schema

Store real evidence outside the public repository. The gate consumes a compact JSON projection such as:

```json
{
  "schema_version": 1,
  "contract_hash": "<sha256 from the current public contract>",
  "disposition": "ready",
  "isolated_restore": {
    "passed": true,
    "functional_verification": true
  },
  "backup_receipt": {
    "observed_at": "2026-01-01T12:00:00Z"
  }
}
```

This public schema deliberately omits repository URLs, snapshot IDs, run IDs, credentials, hostnames, restored object identifiers, screenshots, and other environment evidence. Those remain private.

## Production integration

For a stateful Production deployment, set:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/private/path/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<environment-policy>
```

Then use the normal guarded deployment entry point. There is no stateful routine-update bypass: image updates, redeployments, and explicit historical deployments use the same readiness decision.

Stateless stacks and stacks without a stateful `operations:` declaration do not require recovery evidence.

## Failure semantics

The gate fails closed when:

- the evidence schema is unsupported;
- the contract hash differs;
- the disposition is not `ready`;
- the isolated restore did not pass;
- functional restore verification is absent or false;
- the backup receipt timestamp is invalid, in the future, or older than the supplied freshness policy;
- a stateful Production operation omits private evidence or freshness policy.

Configuration rollback and application-data recovery remain separate mechanisms. Passing this gate does not authorize automatic rollback of persistent data.
