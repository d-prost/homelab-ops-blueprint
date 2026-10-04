# Contributing

I welcome focused contributions that make the transaction model clearer, safer or easier to evaluate.

I prefer small pull requests over changes that mix deployment behavior, documentation and unrelated cleanup. This keeps review proportional to the risk of the change.

## My acceptance baseline

For normal changes I expect:

```bash
make validate
```

For changes to deployment, verification or rollback behavior I also expect the relevant disposable proof, usually:

```bash
make lab-proof
```

I expect tests to change with behavior. I prefer documentation that explains the operational contract and the reason behind a decision instead of repeating implementation details.

## Pull requests

A useful pull request answers three things clearly:

1. the problem being solved;
2. the bounded change that solves it;
3. the evidence used to support it.

I keep unrelated formatting and cleanup out of behavioral PRs. New dependencies, background services or control-plane behavior need a concrete reason that the existing Git + Ansible path cannot satisfy.

## Stack changes

For stack changes I expect these properties to remain true:

- `stack.yml` and `MANIFEST.tsv` describe the same managed boundary;
- remote images are pinned by digest;
- expected services match the Compose model;
- functional checks prove useful runtime behavior;
- private secrets and environment-specific evidence stay outside public Git.

## Reports

The most useful bug reports contain the smallest reproducible case plus the relevant command output. Private hostnames, addresses, credentials, private URLs and recovery evidence do not belong in public reports.

## Writing style

I keep human-facing repository prose in the owner-led style documented in [`docs/WRITING_STYLE.md`](docs/WRITING_STYLE.md).
