# Project Manifest

This repository was intentionally created as a fresh, public-safe derivative blueprint rather than a copy of any private Git history.

## Included capabilities

- guarded manual Production deployment;
- private Production inventory pattern;
- exact-hostname deployment guard, including Ansible Check Mode;
- immutable image digest validation;
- allowlisted file deployment;
- transient transactional rollback for previously managed stacks;
- functional HTTP verification;
- annotated release tags and configuration rollback;
- disposable Lab rollback test for GitHub Actions;
- Gitleaks configuration and complete-history CI scan;
- public/private boundary documentation;
- generic restore-drill template.

## Local validation performed before packaging

- Bash syntax: PASS
- Python compile: PASS
- YAML parsing: PASS
- managed stack contract validation: PASS
- integrity guard tests: PASS
- private-environment identifier scan: PASS

The full Docker + Ansible disposable rollback proof is designed to run in GitHub Actions and was not executed in the artifact-build container.
