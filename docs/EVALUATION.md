# Evaluating the blueprint

This page gives reviewers and prospective adopters a short, reproducible way to evaluate the project without connecting it to an existing Production environment.

## Scope

The evaluation path proves the current public contract:

- repository and stack validation;
- immutable image-reference checks;
- Ansible syntax and contract checks;
- disposable deployment of the reference stack;
- functional verification after deployment;
- an injected failed candidate deployment;
- restoration and re-verification of the previously accepted managed configuration.

It does not prove application-data restore, multi-host deployment or environment-specific Production recovery objectives.

A separate real remote-target proof is required for the v1 SSH evidence goal. The
procedure and public-safe evidence format are documented in
[`REMOTE_SSH_PROOF.md`](REMOTE_SSH_PROOF.md). Documentation alone does not
satisfy that proof; it must be executed against a genuinely separate SSH target.

## Requirements

Use a disposable or non-critical Debian/Ubuntu host with `sudo` access and outbound access to the package and container registries required by the setup.

Clone the repository:

```bash
git clone https://github.com/d-prost/homelab-ops-blueprint.git
cd homelab-ops-blueprint
```

Install the runtime dependencies without deploying a stack:

```bash
bash scripts/setup.sh --install-only
```

## 1. Validate the repository

```bash
make validate
```

Expected result:

```text
Validation passed.
```

This checks the public-safety boundary, stack contracts, functional-check parsing, operational coverage, recovery-readiness logic, integrity guards and Ansible syntax. Optional lint/security tools are used when present; CI runs the strict validation path.

## 2. Prove deployment and rollback

```bash
make lab-proof
```

The proof deploys the public Dozzle reference stack in the local Lab inventory, records the accepted managed configuration, injects a candidate that exits immediately, verifies that the candidate is rejected, restores the previous managed configuration and runs the functional verification again.

Expected result:

```text
Ephemeral Lab rollback proof passed.
```

The test installs only into its disposable Lab target path and removes the test stack and deployment record during cleanup.

## 3. Inspect the control boundaries

For a code review, the most relevant files are:

- `scripts/deploy-stack.sh` — guarded operator entry point;
- `scripts/validate-stack-contracts.py` — stack contract and immutable-image validation;
- `ansible/roles/managed_stack/` — managed-file apply and rollback behavior;
- `scripts/verify-compose-health.py` — target functional verification;
- `scripts/check-recovery-readiness.py` — optional stateful mutation gate;
- `tests/test-lab-rollback.sh` — disposable failure-and-rollback proof;
- `REMOTE_SSH_PROOF.md` — procedure for the external separate-target proof.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full control flow and [`ADOPTION.md`](ADOPTION.md) for adapting the repository to another stack.

## Reporting results

If you test the project outside its own CI, a useful report includes:

- Linux distribution and version;
- Docker Engine and Compose versions;
- Ansible Core version;
- local or remote target;
- which commands were run;
- the smallest reproducible error if something failed.

Do not include credentials, private hostnames, IP addresses, backup locations, deployment receipts or recovery evidence in a public report.
