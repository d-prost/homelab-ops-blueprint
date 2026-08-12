# Project Manifest

This repository is intentionally a fresh public project, not a copy of private operational Git history.

## Included capabilities

- guarded manual Production deployment;
- ignored local Production inventory pattern;
- exact-hostname guard that also works in Ansible Check Mode;
- immutable image digest validation;
- allowlisted file deployment;
- exact source-to-target manifest validation;
- remote-target verification without a target-side repository checkout;
- current control-plane enforcement for historical release deployment;
- transient transactional rollback for previously managed stacks;
- rollback verification against the exact prior Git contract;
- functional HTTP verification;
- annotated operational release tags and configuration rollback;
- disposable Lab rollback proof in GitHub Actions;
- Gitleaks complete-history scanning;
- public-safety validation;
- OpenSSF Scorecard workflow;
- Dependabot configuration and community contribution templates;
- generic restore-drill template;
- generic stateful-service adoption checklist.

## Public-safety design

The repository contains no real Production inventory, private infrastructure address plan, credential, private key, backup receipt, recovery code, or private Git history.

The validation suite rejects a tracked Production inventory, sensitive key/container files, private-key material, private IPv4 addresses except loopback, and internal `home.arpa` hostnames.

## Validation expectations

A public release should have green static validation, a passing disposable rollback proof, no Gitleaks findings, and reviewed OpenSSF Scorecard results.

The repository intentionally invokes shell and Python entry points explicitly in CI and Make targets so correctness does not depend on executable bits surviving browser uploads, ZIP extraction, or cross-platform Git clients.
