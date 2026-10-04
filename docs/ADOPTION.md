# Adapting the repository

The Dozzle and Nginx reference stacks exercise the same deployment contract with different applications. Other Docker Compose stacks can use the same structure.

## Production inventory

Create a local inventory from the example:

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

Production uses strict OpenSSH host-key verification. The target hostname is required; `homelab_expected_machine_id` can optionally pin `/etc/machine-id` as an additional identity check.

Preflight:

```bash
bash scripts/deploy-stack.sh dozzle --check
```

## Stack contract

A stack uses:

```text
stacks/my-stack/
├── compose.yaml
├── defaults.env
├── stack.yml
└── MANIFEST.tsv
```

`stack.yml` defines:

- target directory;
- managed files;
- expected Compose services;
- functional checks.

`MANIFEST.tsv` maps managed source files to target paths. Remote images must be pinned by digest.

Repository validation:

```bash
make validate
```

## Lab path

Check Mode:

```bash
bash scripts/deploy-stack.sh my-stack --check
```

Deployment and rollback behavior can be exercised with:

```bash
make lab-proof
make idempotency-proof
```

The control host serializes each declared target/stack boundary with a host-global lock. v1 assumes one configured control host for a given transaction boundary.

The first managed deployment of a new service has no earlier accepted configuration to restore automatically.

## Production deployment

```bash
bash scripts/deploy-stack.sh my-stack
```

An operational tag can be created after an accepted deployment:

```bash
bash scripts/tag-release.sh
```

Historical stack payloads use the same current guarded deployment path:

```bash
bash scripts/rollback-stack.sh my-stack release-YYYYMMDD-HHMMSSZ
```

The tag supplies the stack payload; current `main` remains authoritative for inventory, validation and deployment logic.

## Acceptance persistence failure

Runtime verification is not sufficient by itself. Acceptance is complete only after the deployment record is durably written.

`ACCEPTANCE_PERSISTENCE_FAILED` leaves an unresolved marker at:

```text
/var/lib/homelab-ops/transactions/<stack>.unresolved
```

New transactions remain blocked until the runtime state, last durable record and storage/permission failure are reconciled.

## Interrupted transactions

The target keeps a minimal durable marker and frozen recovery material.

The next normal invocation classifies the previous state:

- `PREPARED` — cleanup only;
- `MUTATING` / `RESTORING` — restore and reverify the previous accepted configuration;
- `ACCEPTANCE_PENDING` — accepted only when the record and receipt prove the same transaction;
- ambiguous or persistence-failure states — `INTERRUPTED_UNRESOLVED`.

Check Mode does not perform recovery mutation.

## Stateful services

Persistent services define an `operations:` section and follow [`../recovery/STATEFUL_ADOPTION_CHECKLIST.md`](../recovery/STATEFUL_ADOPTION_CHECKLIST.md).

Recovery-readiness inputs:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/path/to/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<seconds>
```

Generation hash:

```bash
python3 scripts/check-recovery-readiness.py \
  stacks/<stack>/stack.yml \
  --print-contract-hash
```

See [`RECOVERY_READINESS.md`](RECOVERY_READINESS.md) for the evidence format.
