# v1 final acceptance

The remaining v1 work is grouped into one final acceptance pass rather than another round of framework changes.

This document describes the sequence; it does not claim the external proofs are already complete.

## Starting state

- clean `main` checkout on the control host;
- private inventory and SSH material outside the repository;
- #37 and #35 still open until their real evidence exists;
- issue #9 remains post-v1 work.

## 1. Main change controls

```bash
bash scripts/configure-main-ruleset.sh
bash scripts/verify-main-ruleset.sh
```

Acceptance evidence for #37:

```text
required check failing -> merge blocked
required checks green   -> merge allowed with zero human approvals
```

The temporary proof PR is closed without merging after both behaviors are observed.

## 2. Real remote SSH proof

Follow [`REMOTE_SSH_PROOF.md`](REMOTE_SSH_PROOF.md).

Initial fact collection:

```bash
HOMELAB_REMOTE_PROOF=1 \
  bash scripts/collect-remote-proof-facts.sh /absolute/path/to/private-hosts.yml
```

Required outcome:

```text
healthy baseline accepted
        ->
failing candidate applied
        ->
REJECTED_ROLLBACK_VERIFIED
        ->
previous functional checks pass again
```

A public-safe evidence record is then created from `docs/evidence/REMOTE_SSH_PROOF_TEMPLATE.md`.

## 3. Final local proof set

After #37 and #35 are complete:

```bash
make validate
make lab-proof
make idempotency-proof
make acceptance-proof
make interruption-proof
make stale-marker-proof
make ssh-interruption-proof
make failure-matrix-proof
```

No new framework scope is added during this pass. Real failures are handled as narrowly scoped fixes and rerun from the affected boundary.

## 4. v1.0.0

After a green final pass:

1. review remaining open issues and keep post-v1 work outside the release boundary;
2. move relevant `CHANGELOG.md` entries into `v1.0.0`;
3. confirm release notes match implemented support;
4. create the release tag:

```bash
git tag -a v1.0.0 -m "HomeLab Ops Blueprint v1.0.0"
git push origin v1.0.0
```
