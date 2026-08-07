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

For each stateless stack define the target directory, exact managed files, expected Compose services, functional HTTP checks, and immutable image digests.

Do not adopt databases or core network services until their rollback and restore boundaries are separately defined.

## 4. First adoption

The first managed deployment has no previous managed-file snapshot. Prove the first adoption in a disposable Lab and keep the previous manual recovery path available.

## 5. Production

Use `--check`, review the diff, deploy explicitly, verify externally, then create an annotated release tag.
