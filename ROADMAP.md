# Roadmap

This is a working list of the next things I want to improve. It is not tied to fixed release dates.

## First stable release criteria

The first stable release is governed by the normative transaction contract in [`docs/TRANSACTION_MODEL.md`](docs/TRANSACTION_MODEL.md). The goal before `v1.0.0` is to prove that contract, not to add platform breadth.

Existing baseline criteria remain:

- focused unit coverage around stack-contract and functional-check parsing;
- at least two stateless reference stacks so the contract is exercised by more than one application shape;
- a clean evaluation path that a new user can run from a fresh checkout;
- at least one external clean-host or remote-target evaluation report, when available, with reproducible compatibility issues fixed or explicitly documented.

The remaining v1 proof work is transaction-focused:

- freeze the candidate and tooling identities before mutation;
- verify SSH transport identity and declared target identity;
- prove rollback material and required immutable images are available before mutation;
- document and prove a real remote-host SSH deployment;
- cover pre-mutation refusals, functional failures, rollback failures and interrupted transactions;
- prove host-global concurrency locking and idempotency;
- define and test durable acceptance-record commit semantics and persistence failure;
- enforce appropriate GitHub `main` change controls for the maintainer model.

Two stateless reference stacks and the clean evaluation path are already present. The remaining release criteria should be completed with real evidence rather than documentation-only claims.

The external-test item is an evidence goal, not a popularity threshold. Stars and download counts are not release criteria.

## Next

- add more unit tests around stack-contract and functional-check parsing;
- repeat the [first separate-target SSH proof](docs/evidence/REMOTE_SSH_PROOF_2026-09-27.md) after material changes to the transaction path;
- cover more failure cases around invalid manifests, target mismatches, failed health checks and incomplete rollback state;
- collect at least one external clean-host or remote-target evaluation report when available;
- prepare the first stable release once those paths have been exercised consistently.

## External validation

The repository should remain easy to evaluate without access to a private HomeLab. The public evaluation path is documented in [`docs/EVALUATION.md`](docs/EVALUATION.md).

Useful external evidence includes successful clean-host validation, a disposable deployment report, a remote-target report, or a reproducible bug report. Public evidence must stay environment-neutral and must not contain private hostnames, addresses, credentials, backup identifiers, deployment receipts or recovery evidence.

The first clean-host evaluation and separate-target SSH transaction proof are
recorded in [the 2026-09-27 evidence report](docs/evidence/REMOTE_SSH_PROOF_2026-09-27.md).

## Deployment records

The current deployment record is intentionally small. I would like to make it more useful without turning it into another control plane:

- retain compatibility with legacy records as the v2 format gains operational use;
- repeat live validation of stable contract, manifest, target and verification IDs after transaction changes;
- repeat runtime proof of candidate failure and rollback-result side records after transaction changes.

## Stateful services

The first readiness gate is implemented, but stateful adoption still needs more work:

- exercise the explicit data, secret-handling, export and restore declarations with a second stateful application shape;
- repeat the [first synthetic Redis recovery proof](docs/evidence/STATEFUL_REDIS_PROOF_2026-09-27.md) after material recovery-path changes;
- expand tests around schema-sensitive changes and rollback compatibility;
- refine the readiness evidence format as real usage exposes gaps.

Configuration rollback and application-data restore will remain separate mechanisms.

## Multi-host support

Once the single-host path has enough real-world coverage:

- repeat [serial and canary group rollout](docs/MULTI_HOST.md) against multiple independent disposable SSH targets;
- verify per-host result reports and partial-group behavior after future transaction changes.

## Later ideas

These are useful only if there is a real need for them:

- repeat deterministic managed-file hashing against copied remote snapshots;
- exercise optional operator signatures on copied accepted records with independent key custody;
- independent verification against Git history;
- exercise the external `--stack-dir --json` validator with another repository's stack;
- extend the read-only configuration drift report with optional live functional checks, without automatic Production changes.
