# Adapting the repository

The example setup uses Dozzle, but the deployment code is meant to work with other Docker Compose stacks as well.

## 1. Configure your host

Create the local Production inventory from the example:

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

Set the Ansible host and the hostname expected on the target.

Run a check before the first deployment:

```bash
bash scripts/deploy-stack.sh dozzle --check
```

## 2. Add a stack

Start with the structure used by `stacks/dozzle/`:

```text
stacks/my-stack/
├── compose.yaml
├── defaults.env
├── stack.yml
└── MANIFEST.tsv
```

In `stack.yml`, define:

- the target directory;
- the files managed by the deployment;
- the Compose services expected after startup;
- functional checks that show the service is actually usable.

`MANIFEST.tsv` must map the managed source files to the same target paths. Container images must use digest-pinned references.

Run the repository validation after adding or changing a stack:

```bash
make validate
```

## 3. Test in the lab

Use Check Mode first:

```bash
bash scripts/deploy-stack.sh my-stack --check
```

For changes to the deployment or rollback code itself, run the disposable integration test as well:

```bash
make lab-proof
```

For a new service, it is worth testing the first real deployment on a disposable or non-critical target before adopting it on the main host. The first deployment has no earlier managed configuration to restore automatically.

## 4. Deploy

Production deployment uses the current clean `main`:

```bash
bash scripts/deploy-stack.sh my-stack
```

After the deployment succeeds, create an operational tag if you want a convenient reference for that accepted stack version:

```bash
bash scripts/tag-release.sh
```

An older tag can later be selected with:

```bash
bash scripts/rollback-stack.sh my-stack release-YYYYMMDD-HHMMSSZ
```

The selected tag supplies the stack payload. The current checkout still supplies the inventory, Ansible role and validation code.

## Stateful stacks

For services with persistent application data, first define the `operations:` section in `stack.yml` and work through [`../recovery/STATEFUL_ADOPTION_CHECKLIST.md`](../recovery/STATEFUL_ADOPTION_CHECKLIST.md).

The Production readiness check expects:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/path/to/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<seconds>
```

To calculate the generation hash used by the readiness file:

```bash
python3 scripts/check-recovery-readiness.py \
  stacks/<stack>/stack.yml \
  --print-contract-hash
```

See [`RECOVERY_READINESS.md`](RECOVERY_READINESS.md) for the evidence format and the fields used by the check.
