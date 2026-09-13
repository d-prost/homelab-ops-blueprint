# Roadmap

This is a working list of the next things I want to improve. It is not tied to fixed release dates.

## First stable release criteria

The first stable release should be based on demonstrated behavior rather than repository age or feature count. Before `v1.0.0`, the project should have:

- focused unit coverage around stack-contract and functional-check parsing;
- at least two stateless reference stacks so the contract is exercised by more than one application shape;
- a documented real remote-host integration run in addition to the local disposable Lab proof;
- regression coverage for important manifest, target-identity, failed-health-check and incomplete-rollback cases;
- a clean evaluation path that a new user can run from a fresh checkout;
- at least one external test or adoption report, when available, with any reproducible compatibility issues either fixed or explicitly documented.

The last item is an evidence goal, not a popularity threshold. Stars and download counts are not release criteria.

## Next

- add more unit tests around stack-contract and functional-check parsing;
- add a second stateless example stack so the contract is exercised by more than Dozzle;
- run and document a real remote-host integration test;
- cover more failure cases around invalid manifests, target mismatches, failed health checks and incomplete rollback state;
- prepare the first stable release once those paths have been exercised consistently.

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
