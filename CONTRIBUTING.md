# Contributing

Focused pull requests are preferred over changes that mix deployment behavior, documentation and unrelated cleanup.

## Validation

The baseline check is:

```bash
make validate
```

Changes to deployment, verification or rollback behavior should also run the relevant disposable proof, usually:

```bash
make lab-proof
```

Behavior changes should include matching tests.

## Pull requests

A useful pull request explains:

1. the problem;
2. the bounded change;
3. the evidence supporting it.

Unrelated formatting changes should stay out of behavioral PRs. New dependencies, background services or control-plane behavior need a clear reason that the existing Git + Ansible path is insufficient.

## Stack changes

Stack changes should preserve these properties:

- `stack.yml` and `MANIFEST.tsv` describe the same managed boundary;
- remote images are pinned by digest;
- expected services match the Compose model;
- functional checks prove useful runtime behavior;
- secrets and environment-specific evidence remain outside public Git.

## Reports

Bug reports are most useful when they contain the smallest reproducible case and relevant non-sensitive output.

Private hostnames, addresses, credentials, private URLs, backup identifiers and recovery evidence should not be posted publicly.
