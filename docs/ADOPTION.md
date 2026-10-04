# Adapting the repository

I use the two stateless reference stacks, Dozzle and Nginx, as examples of the deployment contract rather than as special cases in the implementation.

My adoption path keeps public evaluation separate from private Production assumptions.

## Host identity

I keep the local Production inventory outside public Git:

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

The inventory binds the transaction to an SSH target and expected hostname. I use the normal OpenSSH `known_hosts` trust store with strict host-key checking.

`homelab_expected_machine_id` is optional. I leave it `null` when SSH host-key identity plus hostname is sufficient, and pin the target's 32-character `/etc/machine-id` when I want an additional stable-machine binding.

My preflight path is:

```bash
bash scripts/deploy-stack.sh dozzle --check
```

## Stack contract

I start new stacks from the same shape as `stacks/dozzle/` or `stacks/nginx/`:

```text
stacks/my-stack/
├── compose.yaml
├── defaults.env
├── stack.yml
└── MANIFEST.tsv
```

I use `stack.yml` for:

- target directory;
- managed files;
- expected Compose services;
- functional checks.

I use `MANIFEST.tsv` for the exact managed source-to-target mapping.

Remote images stay digest-pinned.

The repository baseline for a stack change is:

```bash
make validate
```

## Lab path

My first pass is Check Mode:

```bash
bash scripts/deploy-stack.sh my-stack --check
```

For deployment or rollback behavior I use the disposable proofs:

```bash
make lab-proof
make idempotency-proof
```

The control host serializes one declared target/stack boundary with a host-global lock. I deliberately keep v1 to one configured control host for that boundary rather than adding distributed locking.

I treat the first real deployment of a new service as non-reversible by project-managed configuration history because no earlier accepted managed generation exists yet.

## Production path

My normal Production mutation command is:

```bash
bash scripts/deploy-stack.sh my-stack
```

After an accepted deployment I can create an operational tag:

```bash
bash scripts/tag-release.sh
```

A historical stack payload goes through the same current guarded deployment path:

```bash
bash scripts/rollback-stack.sh my-stack release-YYYYMMDD-HHMMSSZ
```

The tag supplies only the historical stack payload. Current `main` remains authoritative for inventory, validation and deployment logic.

## Acceptance persistence failure

Runtime verification alone is not acceptance. I only treat the candidate as accepted after the deployment record has been committed durably.

`ACCEPTANCE_PERSISTENCE_FAILED` leaves the target unresolved and keeps:

```text
/var/lib/homelab-ops/transactions/<stack>.unresolved
```

I treat that marker as a stop condition. I reconcile the runtime state, last durable accepted record and underlying storage or permission failure before clearing it.

## Interrupted transactions

The target keeps a minimal durable marker plus the frozen recovery material needed after control-process or SSH loss.

The next normal invocation classifies the state:

- `PREPARED` — cleanup-only because managed mutation was not crossed;
- `MUTATING` / `RESTORING` — restore and reverify the frozen previous accepted configuration;
- `ACCEPTANCE_PENDING` — accepted only when the durable record and receipt bind the same transaction and record hash;
- `ACCEPTANCE_PERSISTENCE_FAILED` or ambiguous evidence — `INTERRUPTED_UNRESOLVED` until I reconcile it explicitly.

Check Mode does not perform recovery mutation.

## Stateful services

For persistent application data I define the `operations:` section and use the stateful checklist in [`../recovery/STATEFUL_ADOPTION_CHECKLIST.md`](../recovery/STATEFUL_ADOPTION_CHECKLIST.md).

My Production readiness inputs are:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/path/to/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<seconds>
```

The current generation hash comes from:

```bash
python3 scripts/check-recovery-readiness.py \
  stacks/<stack>/stack.yml \
  --print-contract-hash
```

The evidence format is documented in [`RECOVERY_READINESS.md`](RECOVERY_READINESS.md).

## Adoption evidence

When I record an adoption result, I keep the public evidence limited to:

- Linux distribution and version;
- Docker Engine and Compose versions;
- Ansible Core version;
- local or remote target class;
- stack shape;
- command result;
- smallest reproducible non-sensitive failure details.

Private hostnames, addresses, credentials, backup identifiers, deployment receipts and recovery evidence stay outside public GitHub content.
