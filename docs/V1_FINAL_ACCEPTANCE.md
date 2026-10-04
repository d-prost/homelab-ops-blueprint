# v1 final acceptance

I have reached the point where the remaining v1 work belongs in one deliberate acceptance run rather than another round of framework expansion.

This document is my final handoff. It describes the acceptance sequence; it does not claim the remaining manual proofs have already happened.

## Starting state

I begin from a clean `main` checkout on the control host.

Private inventory, SSH material and target-specific evidence stay outside the repository.

The two remaining external gates are:

- #37 — effective GitHub `main` change controls;
- #35 — the real separate-target SSH transaction proof.

Issue #9 remains post-v1 stateful reference work.

## 1. Main change controls

I apply and inspect the ruleset with an identity that has repository `Administration: write`:

```bash
bash scripts/configure-main-ruleset.sh
bash scripts/verify-main-ruleset.sh
```

My #37 acceptance evidence is:

```text
required check failing -> merge blocked
required checks green   -> merge allowed with zero human approvals
```

I use a temporary PR for that proof and close it without merging after both behaviors are observed.

## 2. Real remote SSH proof

I run the separate-target flow documented in:

```text
docs/REMOTE_SSH_PROOF.md
```

My first command is:

```bash
HOMELAB_REMOTE_PROOF=1 \
  bash scripts/collect-remote-proof-facts.sh /absolute/path/to/private-hosts.yml
```

The acceptance path ends as:

```text
healthy baseline accepted
        ->
failing candidate applied
        ->
REJECTED_ROLLBACK_VERIFIED
        ->
previous functional checks pass again
```

After the real run I create the public-safe evidence document from `docs/evidence/REMOTE_SSH_PROOF_TEMPLATE.md`.

I close #35 only after that evidence is committed.

## 3. Final local proof set

After #37 and #35 are complete, I run the full proof set once from the same clean `main`:

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

During this pass I do not add framework scope. A real failure becomes a narrowly scoped fix followed by a rerun from the affected boundary.

## 4. v1.0.0

When the final acceptance pass is green, I:

1. review the remaining open issues and keep post-v1 work outside the release boundary;
2. move the relevant `CHANGELOG.md` entries into `v1.0.0`;
3. confirm that the release notes describe implemented support rather than planned features;
4. create the project tag:

```bash
git tag -a v1.0.0 -m "HomeLab Ops Blueprint v1.0.0"
git push origin v1.0.0
```

Issue #9 and later advisory tooling continue after v1.0.0.
