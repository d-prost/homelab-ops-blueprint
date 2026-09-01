# Roadmap

The roadmap develops **Verified Convergence** rather than maximizing feature count. Every planned capability should strengthen authorization, target identity, bounded mutation, runtime proof, deployment evidence, rollback verification, or recovery readiness.

## Phase 1 — Prove the current convergence model

- deepen unit tests for stack-contract and functional-check parsing;
- add a second stateless reference stack to prove the contract model is reusable;
- add a bounded real remote-target integration proof;
- expand failure-path coverage for invalid contracts, target mismatch, mutable images, incomplete prior state, failed functional checks, rollback verification failure, concurrent mutation, and accidental alternate Production entry points;
- publish the first stable release after the proof suite and Scorecard are consistently green.

Exit criterion: the existing single-host stateless convergence path is reproducible, fail-closed, serialized, and proven beyond the disposable local runner.

## Phase 2 — Make deployment evidence first-class

- evolve the compact deployment record into a versioned machine-readable receipt;
- record deterministic identifiers for the accepted Git commit, stack contract, manifest, target, and verification result;
- add explicit candidate-failure and rollback evidence;
- preserve compatibility with the exact-prior-contract rollback model;
- provide JSON output from validation and verification tools where it creates reusable evidence;
- add an offline verifier that can check receipt integrity against repository history without contacting the target.

Exit criterion: an operator can answer what was authorized, what target accepted it, what was verified, and what rollback state is available from machine-readable evidence.

## Phase 3 — Stateful readiness proof

- keep `operations:` as an explicit operational-coverage contract rather than treating declarations as recovery proof;
- formalize data, secret, export, backup, restore, and functional-restore declarations for stateful stacks;
- model recovery readiness separately from backup existence, including isolated functional restore evidence and an explicit ready/not-ready disposition;
- make backup-receipt freshness an environment-supplied policy derived from the real backup cadence plus bounded operational margin rather than a universal hard-coded age;
- turn the stateful adoption checklist into a machine-checkable Production readiness gate where practical;
- ensure routine image updates, redeployments, and other stateful mutations use the same readiness gate instead of gaining a convenience bypass;
- require explicit proof boundaries before a stateful example can be marked Production-adoptable;
- keep application-data recovery separate from configuration rollback;
- provide public-safe examples without embedding real backup metadata, credentials, topology, or restore evidence.

Current Phase 3 foundation: the guarded Production path now consumes a strict private readiness projection for declared stateful stacks. Evidence is bound to the exact public stack generation, must cover the exact stateful service set, must record isolated functional restore with Production unchanged, and is checked against an environment-supplied backup-freshness policy. Historical payloads cannot erase a stateful classification known to current `main`.

Remaining Phase 3 work includes richer secret/export declarations, a fully synthetic stateful reference example, and any additional evidence schema needed to make the complete adoption boundary machine-checkable without importing private operational truth.

Exit criterion: the project can distinguish mechanically between a declared stateful boundary, a currently recoverable service, and a merely deployable configuration, while preserving one guarded Production mutation path.

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
- one serialized operator deployment path shared by explicit rollback;
- immutable container image digests;
- contract-allowlisted managed files;
- exact source-to-target manifest validation;
- functional target-side verification;
- compact deployment receipt;
- transient transactional rollback of previously managed configuration;
- rollback verification against the exact prior Git contract;
- disposable rollback proof in CI;
- public/private operational boundary;
- operational-coverage validation for stateful declarations;
- stateful adoption and restore-boundary documentation;
- machine-checkable stateful recovery-readiness consumer gate;
- exact public-generation binding for private restore evidence;
- environment-supplied backup-freshness policy;
- fail-closed protection against stateful routine-change and historical-classification bypasses.

## Explicit non-goals

- general cluster orchestration;
- Kubernetes as a project requirement;
- FluxCD or ArgoCD as a required control plane;
- automatic Production deployment from public CI;
- automatic reconciliation merely to claim "GitOps";
- parallel Production maintenance paths or safety bypasses for routine changes;
- storing Production inventory, credentials, backup receipts, readiness evidence, or private operational evidence in the public repository;
- pretending configuration rollback is database or application-data recovery;
- embedding one environment's backup cadence, RPO/RTO targets, or monitoring platform into the reusable core;
- a giant catalogue of self-hosted applications;
- adding governance machinery without demonstrated community need.

The project should remain small enough to understand end to end. A new dependency or abstraction must justify itself by strengthening a Verified Convergence property that cannot be kept simpler otherwise.
