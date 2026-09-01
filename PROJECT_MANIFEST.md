# Project Manifest

This repository is intentionally a fresh public project, not a copy of private operational Git history.

Its central engineering idea is **Verified Convergence**: a Production state is accepted only through an explicit chain from reviewed Git intent to exact target identity, contract-bounded mutation, functional runtime verification, recorded deployment evidence, and verified rollback to the exact previously accepted contract when convergence fails.

## Verified Convergence capabilities

### Authorized desired state

- guarded manual Production convergence;
- clean-tree, branch, and remote-equality enforcement;
- current control-plane authority when deploying historical release payloads;
- annotated operational release tags.

### Exact target identity

- ignored local Production inventory pattern;
- exact-hostname guard that also works in Ansible Check Mode;
- remote-target verification without a target-side repository checkout.

### Contract-bounded mutation

- stack contracts with explicit target directories and managed files;
- allowlisted file deployment;
- exact source-to-target `MANIFEST.tsv` validation;
- immutable image digest validation.

### Functional runtime proof

- expected Compose service verification;
- target-side functional HTTP verification;
- disposable Lab deployment and rollback proof in GitHub Actions.

### Acceptance evidence

- deployment record containing the accepted stack, Git commit, target, and verification class;
- Git history retained as the authoritative source for the exact prior accepted contract.

### Verified rollback

- transient transactional rollback for previously managed configuration;
- complete prior managed-file capture before candidate mutation when rollback is provable;
- candidate-only file removal on failed convergence;
- rollback verification against the exact prior Git contract;
- fail-closed behavior when a verified rollback boundary is unavailable.

### Stateful recovery readiness

- operational-coverage validation remains separate from recovery proof;
- Production readiness consumes a compact private JSON projection rather than private restore records;
- readiness evidence is bound to the public stack identity and exact generation, including managed payload and restore-runbook hashes;
- exact stateful-service coverage is required;
- isolated restore, functional verification, Production unchanged, and explicit `ready` disposition are required;
- private RPO and RTO targets remain private while the projection must confirm both objectives were met;
- configuration rollback must be explicitly confirmed compatible with the candidate before the guarded stateful path is allowed;
- backup freshness is supplied by the private environment rather than hard-coded publicly;
- private evidence must live outside the public repository tree and must not be group- or world-writable;
- historical payloads cannot silently erase a stateful classification known to current `main`;
- routine stateful mutations reuse the single guarded Production path.

### Public-safe operation

- Gitleaks complete-history scanning;
- public-safety validation;
- explicit public/private operational boundary;
- OpenSSF Scorecard workflow;
- Dependabot configuration and community contribution templates.

### Recovery boundary

- generic restore-drill template;
- generic stateful-service adoption checklist;
- strict public/private readiness-evidence consumer contract;
- explicit separation between configuration convergence and application-data recovery.

## Public-safety design

The repository contains no real Production inventory, private infrastructure address plan, credential, private key, backup receipt, readiness record, recovery code, or private Git history.

The validation suite rejects a tracked Production inventory, sensitive key/container files, private-key material, private IPv4 addresses except loopback, and internal `home.arpa` hostnames. Recovery readiness tests use only synthetic data and verify that private evidence is consumed from outside the public repository tree.

## Validation expectations

A public release should have green static validation, a passing disposable rollback proof, no Gitleaks findings, and reviewed OpenSSF Scorecard results.

Safety-sensitive changes should preserve the Verified Convergence chain. Convenience alone is not sufficient justification for weakening Git authorization, target identity, immutable images, mutation boundaries, runtime verification, deployment evidence, rollback proof, or stateful recovery readiness.

The repository intentionally invokes shell and Python entry points explicitly in CI and Make targets so correctness does not depend on executable bits surviving browser uploads, ZIP extraction, or cross-platform Git clients.
