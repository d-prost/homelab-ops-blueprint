# Roadmap

This is a working list of the next things I want to improve. It is not tied to fixed release dates.

## Next

- add more unit tests around stack-contract and functional-check parsing;
- add a second stateless example stack so the contract is exercised by more than Dozzle;
- run and document a real remote-host integration test;
- cover more failure cases around invalid manifests, target mismatches, failed health checks and incomplete rollback state;
- prepare the first stable release once those paths have been exercised consistently.

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
