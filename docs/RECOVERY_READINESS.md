# Recovery Readiness Gate

Stateful deployment safety requires a separate recovery decision. A valid Compose model, a successful configuration rollback path, or the existence of a backup does not prove that application data is currently recoverable.

The public blueprint therefore defines a **consumer-side readiness gate**. It does not write backups, store credentials, know private repository locations, or publish real restore evidence.

## Decision model

For a stateful stack, Production readiness is accepted only when all of these are true:

1. the public `operations:` contract declares the state boundary;
2. private evidence is bound to the exact public stack name and generation for which recovery was proven;
3. the evidence explicitly covers the complete stateful service set;
4. an isolated restore passed without changing Production;
5. the restored service passed functional verification, not only a container or file-existence check;
6. the environment confirms its applicable RPO and RTO objectives were met;
7. configuration rollback to the previously accepted deployment state is safe for this candidate;
8. the private evidence has an explicit `ready` disposition;
9. backup evidence is fresh enough for an environment-supplied policy.

The freshness policy is intentionally not embedded in this repository. A real environment derives it from its backup cadence plus a bounded operational margin and passes the resulting maximum age to the gate. When a stack depends on more than one required backup input, `backup_receipt.observed_at` must represent the **oldest required applicable backup evidence**, so one fresh component cannot hide a stale dependency.

RPO/RTO target values remain private environment decisions. The public projection carries only `rpo_met` and `rto_met` booleans.

## Exact public-generation binding

A restore proof can become obsolete even when mount and backup declarations did not change. An image upgrade, database-engine change, Compose change, public application configuration change, or restore-runbook change can alter recovery compatibility.

The gate therefore hashes a versioned recovery-proof contract containing:

- the public stack name, preventing cross-stack evidence replay;
- stateful `persistent_mounts`, `backup`, and `restore` declarations;
- expected services and functional deployment checks;
- the declared managed-file contract;
- SHA-256 digests of every managed public payload file, including Compose and public defaults;
- SHA-256 digests of referenced restore runbooks.

A change to those inputs invalidates older evidence automatically. Monitoring-only intent does not invalidate an otherwise applicable restore proof.

Generate the current hash with:

```bash
python3 scripts/check-recovery-readiness.py \
  stacks/<stack>/stack.yml \
  --print-contract-hash
```

The hash is an applicability identifier, not a signature. Authenticity of the private evidence source remains an operator trust decision.

## Private evidence schema

Store the compact readiness projection outside the public repository tree. The accepted schema is intentionally strict:

```json
{
  "schema_version": 1,
  "contract_hash": "<sha256 from the exact public stack generation>",
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

Unknown fields are rejected. Real RPO/RTO values, repository URLs, Snapshot IDs, Run IDs, credentials, hostnames, restored object identifiers, screenshots, and detailed drill evidence remain private and are not part of the public consumer contract.

`configuration_rollback_safe` is deliberately separate from restore success. It asserts that returning to the previously accepted image/configuration generation after candidate verification failure will not create an unsafe data/schema mismatch. Schema-sensitive, migration-heavy, database-major, or otherwise rollback-incompatible changes must not be represented as ready for this guarded path.

The evidence file must be a regular non-symlink file, must not be group- or world-writable, and must live outside the public repository tree. These checks prevent an ignored file inside the public clone or an easily replaceable local file from silently becoming Production authorization input.

## Production integration

For a stateful Production deployment, set:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/private/path/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<environment-policy>
```

Then use the normal guarded deployment entry point. There is no stateful routine-update bypass: image updates, redeployments, Check Mode previews through the Production path, and explicit historical deployments use the same readiness decision.

The current `main` stack contract is also supplied to the gate. If current `main` declares the stack stateful but a selected historical payload predates the stateful recovery contract, the operation fails closed instead of silently classifying that historical payload as stateless.

Stateless stacks whose current and selected contracts are both stateless do not require recovery evidence.

## Failure semantics

The gate fails closed when:

- the evidence schema is unsupported, incomplete, or contains unknown fields;
- the evidence file violates its local trust boundary;
- the contract hash differs from the selected public stack generation or stack identity;
- the evidence does not cover the exact stateful service set;
- the disposition is not `ready`;
- the isolated restore, functional verification, or Production-isolation assertion is false;
- RPO or RTO objectives are not confirmed as met;
- configuration rollback is not confirmed safe for the candidate;
- the backup receipt timestamp is invalid, in the future, or older than the supplied freshness policy;
- a stateful Production operation omits private evidence or freshness policy;
- a historical payload would erase a stateful classification known to the current control plane.

Configuration rollback and application-data recovery remain separate mechanisms. Passing this gate does not authorize automatic rollback of persistent data.

## Phase 3 boundary

This gate is a Phase 3 foundation, not a claim that the entire stateful model is complete. The remaining roadmap work includes richer public declarations for secret and export boundaries, a fully synthetic stateful reference example, and stronger machine-readable evidence where it adds independent verification without importing private operational truth.
