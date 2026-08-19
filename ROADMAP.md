# Roadmap

The roadmap develops **Verified Convergence** rather than maximizing feature count. Every planned capability should strengthen authorization, target identity, bounded mutation, runtime proof, deployment evidence, rollback verification, or recovery readiness.

## Phase 1 — Prove the current convergence model

- deepen unit tests for stack-contract and functional-check parsing;
- add a second stateless reference stack to prove the contract model is reusable;
- add a bounded real remote-target integration proof;
- expand failure-path coverage for invalid contracts, target mismatch, mutable images, incomplete prior state, failed functional checks, and rollback verification failure;
- publish the first stable release after the proof suite and Scorecard are consistently green.

Exit criterion: the existing single-host stateless convergence path is reproducible, fail-closed, and proven beyond the disposable local runner.

## Phase 2 — Make deployment evidence first-class

- evolve the compact deployment record into a versioned machine-readable receipt;
- record deterministic identifiers for the accepted Git commit, stack contract, manifest, target, and verification result;
- add explicit candidate-failure and rollback evidence;
- preserve compatibility with the exact-prior-contract rollback model;
- provide JSON output from validation and verification tools where it creates reusable evidence;
- add an offline verifier that can check receipt integrity against repository history without contacting the target.

Exit criterion: an operator can answer what was authorized, what target accepted it, what was verified, and what rollback state is available from machine-readable evidence.

## Phase 3 — Stateful readiness proof

- formalize data, secret, export, backup, restore, and functional-restore declarations for stateful stacks;
- turn the stateful adoption checklist into a machine-checkable readiness gate where practical;
- require explicit proof boundaries before a stateful example can be marked Production-adoptable;
- keep application-data recovery separate from configuration rollback;
- provide public-safe examples without embedding real backup metadata or credentials.

Exit criterion: the project can distinguish, mechanically where possible, between a deployable configuration and a recoverable stateful service.

## Phase 4 — Multi-host Verified Convergence

- introduce reusable inventory groups and explicit stack-to-target selection;
- retain exact host-identity checks for every target;
- add serial and canary convergence modes before broader rollout;
- produce per-host deployment receipts;
- define partial-fleet failure behavior and fail-closed stopping conditions;
- add a fleet convergence report that distinguishes accepted, rolled-back, failed, and untouched targets.

Exit criterion: multi-host operation preserves the same proof properties as single-host deployment instead of bypassing them for convenience.

## Phase 5 — Independent and stronger verification

Only after the previous phases are proven by real use:

- deterministic contract hashing and evidence-chain verification;
- optional signing of deployment evidence;
- replay checks against Git history;
- reusable validation action or package when external repositories demonstrate a need;
- selective drift detection that reports divergence without silently introducing an always-on reconciliation controller.

Exit criterion: acceptance evidence can be independently checked and remains useful outside the original control-plane session.

## Completed foundations

- reviewed Git as desired state;
- current-control-plane authority over historical payloads;
- remote targets without repository checkouts;
- exact target-hostname guard;
- immutable container image digests;
- contract-allowlisted managed files;
- exact source-to-target manifest validation;
- functional target-side verification;
- compact deployment receipt;
- transient transactional rollback of previously managed configuration;
- rollback verification against the exact prior Git contract;
- disposable rollback proof in CI;
- public/private operational boundary;
- stateful adoption and restore-boundary documentation.

## Explicit non-goals

- general cluster orchestration;
- Kubernetes as a project requirement;
- FluxCD or ArgoCD as a required control plane;
- automatic Production deployment from public CI;
- automatic reconciliation merely to claim "GitOps";
- storing Production inventory, credentials, or private operational evidence in the public repository;
- pretending configuration rollback is database or application-data recovery;
- a giant catalogue of self-hosted applications;
- adding governance machinery without demonstrated community need.

The project should remain small enough to understand end to end. A new dependency or abstraction must justify itself by strengthening a Verified Convergence property that cannot be kept simpler otherwise.
