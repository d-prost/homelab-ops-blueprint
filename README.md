> [!NOTE]
> Active development has moved to two successor projects:
>
> - [DeployInvariant](https://github.com/d-prost/deploy-invariant) — the reusable deployment transaction mechanism.
> - [HomeLab Engineering](https://github.com/d-prost/homelab-engineering) — public architecture decisions, experiments and operational lessons.
>
> This repository is retained as the public development history that preceded both projects. It is no longer the canonical location for new work.

# HomeLab Ops Blueprint

A compact Git + Ansible workflow for safer Docker Compose changes without introducing a full orchestration platform.

I built it for small homelab environments where starting containers is easy, but repeatable changes, verification and rollback need more discipline.

[![Validate blueprint](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml/badge.svg)](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/d-prost/homelab-ops-blueprint/badge)](https://securityscorecards.dev/viewer/?uri=github.com/d-prost/homelab-ops-blueprint)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Scope

The project currently targets single-host Docker Compose deployments and provides:

- Git-reviewed stack definitions;
- SSH target identity checks before mutation;
- digest-pinned container images;
- functional checks after deployment;
- durable acceptance records;
- bounded configuration rollback;
- separate recovery-readiness checks for stateful services.

It is not intended to replace a scheduler, service mesh, secrets manager, backup system or general-purpose control plane.

## How it works

A Git commit is treated as a deployment candidate, not as proof that Production is healthy.

```text
candidate
   |
   v
preflight + target identity
   |
   v
contract + image checks
   |
   v
managed mutation
   |
   v
functional verification
   |
   +--> PASS -> durable acceptance -> ACCEPTED
   |
   +--> FAIL -> restore previous config -> reverify
```

Configuration rollback and application-data recovery are separate concerns. Stateful services can require matching recovery evidence before a Production mutation is allowed.

The transaction semantics are documented in [`docs/TRANSACTION_MODEL.md`](docs/TRANSACTION_MODEL.md).

## Reference stacks

Two stateless stacks exercise the same deployment contract with different applications:

- `stacks/dozzle/`
- `stacks/nginx/`

Each stack contains:

```text
stacks/<name>/
├── compose.yaml
├── defaults.env
├── stack.yml
└── MANIFEST.tsv
```

`stack.yml` defines the target boundary, expected services and functional checks. `MANIFEST.tsv` maps managed source files to target paths.

## Quick start

On Debian or Ubuntu:

```bash
git clone https://github.com/d-prost/homelab-ops-blueprint.git
cd homelab-ops-blueprint
bash scripts/setup.sh
```

Install dependencies and validate the checkout without deploying a reference stack:

```bash
bash scripts/setup.sh --install-only
make validate
```

Deploy the Nginx example instead:

```bash
bash scripts/setup.sh --stack nginx
```

## Production

Create a local inventory from the example and keep the real values outside public Git:

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

Production uses strict OpenSSH host-key verification and a clean `main` matching `origin/main`.

Preflight:

```bash
bash scripts/deploy-stack.sh dozzle --check
```

Deployment:

```bash
bash scripts/deploy-stack.sh dozzle
```

Transactions for the same target/stack boundary are serialized on the configured control host. v1 deliberately does not add distributed locking across multiple control hosts.

## Stateful services

Stateful stacks can require a recovery-readiness file and backup-age policy:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/path/to/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<seconds>
```

Recovery evidence is tied to the recovery-relevant stack generation. Configuration rollback never implies application-data rollback.

See [`docs/RECOVERY_READINESS.md`](docs/RECOVERY_READINESS.md).

## Validation

The main proof commands are:

```bash
make validate
make lab-proof
make idempotency-proof
make acceptance-proof
make interruption-proof
make stale-marker-proof
make ssh-interruption-proof
make failure-matrix-proof
```

GitHub Actions runs the matching static and disposable checks. CI validates the repository and transaction behavior; it does not deploy Production.

## Repository layout

| Path | Purpose |
|---|---|
| `ansible/` | inventories, playbooks and deployment role |
| `stacks/` | Docker Compose stack contracts and payloads |
| `scripts/` | setup, deployment, rollback and validation helpers |
| `tests/` | contract and disposable transaction proofs |
| `recovery/` | stateful adoption and restore-drill material |
| `advisory/` | reusable operational lessons |
| `docs/` | architecture, adoption, recovery and release documentation |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Transaction model](docs/TRANSACTION_MODEL.md)
- [Adoption](docs/ADOPTION.md)
- [Evaluation](docs/EVALUATION.md)
- [Recovery readiness](docs/RECOVERY_READINESS.md)
- [Operational lessons](docs/OPERATIONAL_LESSONS.md)
- [Main change controls](docs/MAIN_CHANGE_CONTROLS.md)
- [Real remote SSH proof](docs/REMOTE_SSH_PROOF.md)
- [v1 final acceptance](docs/V1_FINAL_ACCEPTANCE.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)

## Status

The single-host stateless transaction path is implemented and covered by disposable proofs. The remaining v1 release gates are the real separate-target SSH proof and effective GitHub `main` protection.

Stateful reference recovery, richer deployment records and multi-host rollout remain follow-up work.

## License

MIT. See [`LICENSE`](LICENSE).
