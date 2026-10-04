# Evaluating the blueprint

This is the public evaluation path I use to prove the repository contract without depending on a private Production environment.

## Scope

The evaluation covers:

- repository and stack validation;
- immutable image references;
- Ansible syntax and contract checks;
- disposable deployment;
- functional verification;
- injected candidate failure;
- restoration of the previous managed configuration;
- functional re-verification after rollback.

It does not claim application-data recovery, multi-host rollout or environment-specific Production recovery objectives.

The real separate-target SSH evidence is a different proof and remains documented in [`REMOTE_SSH_PROOF.md`](REMOTE_SSH_PROOF.md).

## Clean-host baseline

My disposable evaluation target is a non-critical Debian or Ubuntu host with `sudo` and outbound access to the required package and container registries.

The checkout path is:

```bash
git clone https://github.com/d-prost/homelab-ops-blueprint.git
cd homelab-ops-blueprint
bash scripts/setup.sh --install-only
```

## Repository validation

```bash
make validate
```

Expected terminal output:

```text
Validation passed.
```

This covers public-safety checks, stack contracts, functional-check parsing, operational coverage, recovery-readiness logic, integrity guards and Ansible syntax.

## Deployment and rollback proof

```bash
make lab-proof
```

Expected terminal output:

```text
Ephemeral Lab rollback proof passed.
```

The proof accepts a healthy baseline, injects a failing candidate, restores the previous managed configuration, reruns the functional checks and cleans its disposable state.

## Control boundaries I review

The files I treat as the most important review surfaces are:

- `scripts/deploy-stack.sh` — guarded mutation entry point;
- `scripts/validate-stack-contracts.py` — stack contract and immutable-image validation;
- `ansible/roles/managed_stack/` — managed apply and rollback behavior;
- `scripts/verify-compose-health.py` — target functional verification;
- `scripts/check-recovery-readiness.py` — stateful mutation gate;
- `tests/test-lab-rollback.sh` — disposable rollback proof;
- `REMOTE_SSH_PROOF.md` — real separate-target evidence path.

[`ARCHITECTURE.md`](ARCHITECTURE.md) contains the full control flow.

## Public evidence

When I publish an evaluation result, I keep it to:

- OS distribution/version;
- Docker Engine and Compose versions;
- Ansible Core version;
- local or remote target class;
- commands executed;
- smallest reproducible non-sensitive failure.

Credentials, private hostnames, addresses, backup locations, deployment receipts and recovery evidence remain outside public reports.
