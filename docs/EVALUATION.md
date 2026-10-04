# Evaluation

This is the public evaluation path for the current repository contract without depending on a private Production environment.

## Coverage

The evaluation covers:

- repository and stack validation;
- immutable image references;
- Ansible syntax and contract checks;
- disposable deployment;
- functional verification;
- injected candidate failure;
- restoration of the previous managed configuration;
- functional re-verification after rollback.

It does not prove application-data recovery, multi-host rollout or environment-specific recovery objectives.

The separate-target SSH proof is documented in [`REMOTE_SSH_PROOF.md`](REMOTE_SSH_PROOF.md).

## Clean-host baseline

A disposable Debian or Ubuntu host with `sudo` and outbound package/container-registry access is sufficient.

```bash
git clone https://github.com/d-prost/homelab-ops-blueprint.git
cd homelab-ops-blueprint
bash scripts/setup.sh --install-only
```

## Repository validation

```bash
make validate
```

Expected result:

```text
Validation passed.
```

## Deployment and rollback proof

```bash
make lab-proof
```

Expected result:

```text
Ephemeral Lab rollback proof passed.
```

The proof accepts a healthy baseline, injects a failing candidate, restores the previous managed configuration, reruns functional checks and removes its disposable state.

## Useful review surfaces

- `scripts/deploy-stack.sh`
- `scripts/validate-stack-contracts.py`
- `ansible/roles/managed_stack/`
- `scripts/verify-compose-health.py`
- `scripts/check-recovery-readiness.py`
- `tests/test-lab-rollback.sh`
- `REMOTE_SSH_PROOF.md`

The complete control flow is described in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Public evidence

Published evaluation notes should contain only non-sensitive compatibility and result data such as OS, Docker, Compose and Ansible versions, target class, commands used and reproducible errors.

Credentials, private hostnames, addresses, backup locations, deployment receipts and recovery evidence remain outside public reports.
