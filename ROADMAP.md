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

## Final v1 acceptance

The implementation work for the single-host stateless transaction path is
substantially complete. The remaining release work should now be handled as one
operator acceptance pass rather than by adding more framework behavior.

Use [`docs/V1_FINAL_ACCEPTANCE.md`](docs/V1_FINAL_ACCEPTANCE.md) for the final
sequence:

- apply and prove the GitHub `main` ruleset required by issue #37;
- execute the real separate-target SSH proof required by issue #35;
- run the complete local proof set once from a clean `main` checkout;
- prepare and tag `v1.0.0` if that acceptance pass is green.

Additional parser coverage, failure cases and external reports remain useful, but
they should not expand the release boundary unless the final acceptance run
exposes a concrete defect.

## External validation

The repository should remain easy to evaluate without access to a private HomeLab. The public evaluation path is documented in [`docs/EVALUATION.md`](docs/EVALUATION.md).

Useful external evidence includes successful clean-host validation, a disposable deployment report, a remote-target report, or a reproducible bug report. Public evidence must stay environment-neutral and must not contain private hostnames, addresses, credentials, backup identifiers, deployment receipts or recovery evidence.

## Deployment records

The current deployment record is intentionally small. I would like to make it more useful without turning it into another control plane:

- version the record format;
- include stable identifiers for the stack contract, manifest, target and verification result;
- record candidate failures and rollback results more clearly;
- add JSON output where it is useful for tooling;
- add an offline command that can compare a deployment record with repository history.

## Stateful services

The first readiness gate is implemented, but stateful adoption still needs more work:

- improve declarations for data, secrets, exports and restore procedures;
- add a fully synthetic stateful example that can be tested end to end;
- expand tests around schema-sensitive changes and rollback compatibility;
- refine the readiness evidence format as real usage exposes gaps.

Configuration rollback and application-data restore will remain separate mechanisms.

## Multi-host support

Once the single-host path has enough real-world coverage:

- support reusable inventory groups and explicit stack-to-host selection;
- add serial and canary deployment modes;
- keep a deployment result per host;
- define clear behavior when only part of a group deploys successfully.

## Later ideas

These are useful only if there is a real need for them:

- deterministic hashes for more deployment artifacts;
- optional signing of deployment records;
- independent verification against Git history;
- reusable validation tooling for other repositories;
- drift reporting that reports differences without automatically changing Production.
