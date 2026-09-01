# Adopting the Blueprint

## 1. Fork or create a fresh repository

Do not preserve history from a private operational repository.

## 2. Keep Production inventory local/private

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

The real file is ignored by Git.

## 3. Replace the demo stack gradually

For each stateless stack define the target directory, exact managed files, a matching source-to-target `MANIFEST.tsv`, expected Compose services, functional HTTP checks, and immutable image digests.

The control plane must keep the current inventory, playbooks, roles, verification code, and recovery-readiness logic authoritative. A historical release may supply only the selected stack payload. Remote targets do not need a Git checkout.

Do not adopt databases or core network services until their rollback and restore boundaries are separately defined. Use [the stateful adoption checklist](../recovery/STATEFUL_ADOPTION_CHECKLIST.md).

For a stateful stack, add the public `operations:` declaration and produce the private readiness projection described in [Recovery Readiness](RECOVERY_READINESS.md). The private projection must stay outside the public repository tree and should be generated only from real private backup/restore evidence after the applicable recovery objectives have been evaluated.

Generate the exact public stack-generation hash with:

```bash
python3 scripts/check-recovery-readiness.py \
  stacks/<stack>/stack.yml \
  --print-contract-hash
```

A material image, Compose, managed configuration, storage, backup, restore, or runbook change changes that hash and requires new applicable private readiness evidence before the next stateful Production operation.

## 4. First adoption

The first managed deployment has no previous managed-file snapshot. Prove the first adoption in a disposable Lab and keep the previous manual recovery path available.

For a stateful first adoption, complete an isolated functional restore before setting the private disposition to `ready`. A successful snapshot or running container is not sufficient evidence.

## 5. Production

Use `--check`, review the diff, deploy explicitly, verify externally, then create an annotated release tag. The first real remote deployment is a required proof: local-connection CI cannot prove that control-plane-only paths were separated correctly.

For a declared stateful stack, both Production Check Mode and real convergence require:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/private/path/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<environment-policy>
```

Do not add a wrapper that skips this requirement for routine image updates or historical redeployments. If current `main` declares a stack stateful and an old release predates the recovery contract, the guarded path intentionally fails closed rather than treating the historical payload as stateless.
