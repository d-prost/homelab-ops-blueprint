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

The control plane must keep the current inventory, playbooks, roles, and verification code authoritative. A historical release may supply only the selected stack payload. Remote targets do not need a Git checkout.

Do not adopt databases or core network services until their rollback and restore boundaries are separately defined. Use [the stateful adoption checklist](../recovery/STATEFUL_ADOPTION_CHECKLIST.md).

## 4. First adoption

The first managed deployment has no previous managed-file snapshot. Prove the first adoption in a disposable Lab and keep the previous manual recovery path available.

## 5. Production

Use `--check`, review the diff, deploy explicitly, verify externally, then create an annotated release tag. The first real remote deployment is a required proof: local-connection CI cannot prove that control-plane-only paths were separated correctly.
