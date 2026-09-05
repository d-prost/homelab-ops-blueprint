# Contributing

Contributions are welcome. Small, focused pull requests are much easier to review than changes that mix deployment logic, documentation and unrelated cleanup.

## Before opening a pull request

Run the normal validation suite:

```bash
make validate
```

If you changed deployment, verification or rollback behavior, also run:

```bash
make lab-proof
```

Add or update tests when you change behavior. Documentation changes should describe what an operator actually needs to know rather than restating implementation details.

## Pull requests

A useful pull request description answers three questions:

1. What problem does this solve?
2. What changed?
3. How was it tested?

Please avoid unrelated formatting changes in the same PR. If a new dependency or background service is needed, explain why the existing scripts and Ansible path are not enough.

## Stack changes

When adding or changing a stack, make sure:

- `stack.yml` and `MANIFEST.tsv` describe the same managed files;
- image references are pinned by digest;
- expected services and functional checks match the Compose model;
- `make validate` passes.

## Bug reports

Include the smallest reproducible example you can, along with the relevant validation or command output. Redact credentials and environment-specific details from logs or configuration before posting them publicly.
