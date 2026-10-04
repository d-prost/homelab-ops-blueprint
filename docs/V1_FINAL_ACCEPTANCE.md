# v1 final acceptance

The repository is at the point where the remaining v1 work should be finished as
one deliberate operator run rather than through more incremental framework work.

This document is the handoff for that run. It does not claim that the steps
below have been executed.

## Before the final run

Use a clean checkout of `main` on the control host and keep any private
inventory, SSH material and target-specific evidence outside the repository.

The two open v1 evidence items are intentionally manual:

- issue #37: apply and prove the GitHub `main` change controls;
- issue #35: execute the transaction path against a genuinely separate SSH
  target.

The synthetic stateful reference stack in issue #9 is follow-up work. It is not
part of this final single-host stateless transaction acceptance run.

## 1. Apply the GitHub main ruleset

Run with a GitHub CLI identity that has repository `Administration: write`:

```bash
bash scripts/configure-main-ruleset.sh
bash scripts/verify-main-ruleset.sh
```

Then perform the blocked-merge proof required by issue #37:

1. open a temporary pull request;
2. make one required machine check fail intentionally;
3. confirm GitHub refuses the merge;
4. restore the change;
5. confirm the all-green pull request is mergeable with zero human approvals;
6. close the temporary pull request without merging it.

Close #37 only after GitHub reports the effective rules and both merge behaviors
have been observed.

## 2. Execute the real remote SSH proof

Use a disposable or non-critical machine that is genuinely separate from the
control host.

Follow:

```text
docs/REMOTE_SSH_PROOF.md
```

Start by collecting the public-safe facts:

```bash
HOMELAB_REMOTE_PROOF=1 \
  bash scripts/collect-remote-proof-facts.sh /absolute/path/to/private-hosts.yml
```

The proof should finish with:

```text
healthy baseline accepted
        ->
failing candidate applied
        ->
REJECTED_ROLLBACK_VERIFIED
        ->
previous functional checks pass again
```

Create the public evidence document from
`docs/evidence/REMOTE_SSH_PROOF_TEMPLATE.md` only after the real run. Do not
publish private addresses, hostnames, usernames, SSH material, deployment
records or recovery evidence.

Close #35 only after that evidence is committed.

## 3. Run the final local proof set

Once #37 and #35 are complete, run the full local proof set from the same clean
`main` checkout:

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

The intent is one final acceptance pass. Do not add new framework behavior while
this run is in progress. A real failure should become a narrowly scoped fix and
be rerun from the affected boundary.

## 4. Prepare v1.0.0

After the final run is green:

1. review the remaining open issues and keep post-v1 work out of the release
   boundary;
2. move the relevant `Unreleased` entries in `CHANGELOG.md` into
   `v1.0.0`;
3. confirm the release notes describe the actual supported boundary rather than
   planned features;
4. create the project tag:

```bash
git tag -a v1.0.0 -m "HomeLab Ops Blueprint v1.0.0"
git push origin v1.0.0
```

Issue #9 and the read-only advisory tooling can continue after v1.0.0 without
holding the first stable release open.
