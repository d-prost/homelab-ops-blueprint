# Adapting the repository

The repository includes two stateless reference stacks, Dozzle and Nginx, so the deployment contract can be inspected against more than one application shape. The deployment code is intended to work with other Docker Compose stacks as well.

Before adapting it to an existing environment, use the disposable evaluation path in [`EVALUATION.md`](EVALUATION.md) on a non-critical host. That separates evaluation of the public workflow from any private Production assumptions.

## 1. Configure your host

Create the local Production inventory from the example:

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

Set the SSH target, operator user and hostname expected on the target. Production
uses the normal OpenSSH `known_hosts` trust store with strict host-key
verification. Add the target's trusted SSH host key before the first run; an
unknown or changed host key is a refusal, not an interactive trust prompt.

`homelab_expected_machine_id` is optional. Leave it `null` when hostname +
SSH host-key identity is sufficient, or set it to the target's 32-character
`/etc/machine-id` value for an additional stable-machine binding.

Run a check before the first deployment:

```bash
bash scripts/deploy-stack.sh dozzle --check
```

## 2. Add a stack

Start with the structure used by `stacks/dozzle/` or `stacks/nginx/`:

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

For changes to the deployment or rollback code itself, run the disposable integration tests as well:

```bash
make lab-proof
make idempotency-proof
```

The control host serializes the same declared target/stack boundary with a
host-global lock shared across local operator users. This is intentionally not
a distributed lock: v1 assumes one configured control host for a given
target/stack transaction boundary.

For a new service, test the first real deployment on a disposable or non-critical target before adopting it on the main host. The first deployment has no earlier managed configuration to restore automatically.

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

## Report an adoption result

Reports from environments outside the repository's own CI are useful because they expose assumptions that a single maintainer's setup may not reveal.

A useful public report includes:

- Linux distribution and version;
- Docker Engine and Compose versions;
- Ansible Core version;
- local or remote target;
- which stack or custom stack was used;
- whether `make validate`, Check Mode and the deployment succeeded;
- the smallest reproducible error if something failed.

Use a GitHub Issue for reproducible defects or a Discussion for general adoption feedback. Keep private hostnames, addresses, credentials, backup identifiers, deployment receipts and recovery evidence out of public GitHub content.

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
