# HomeLab Ops Blueprint

A small Git + Ansible workflow I use to make Docker Compose changes predictable, reviewable and reversible without adding a full orchestration platform.

[![Validate blueprint](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml/badge.svg)](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/d-prost/homelab-ops-blueprint/badge)](https://securityscorecards.dev/viewer/?uri=github.com/d-prost/homelab-ops-blueprint)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

I built this for homelab-sized environments where starting containers is easy, but changing them safely is the harder problem. Git holds the desired stack payload, Ansible applies it, and I only treat a candidate as accepted after the target passes the required checks.

The current boundary is intentionally narrow: single-host Docker Compose, explicit target verification, immutable images, functional acceptance, durable acceptance evidence, bounded configuration rollback and separate recovery-readiness evidence for stateful services.

## Scope

I use this project when I want:

- Git-reviewed and reproducible Docker Compose changes;
- one guarded mutation path instead of several maintenance shortcuts;
- target identity checks before mutation;
- application-level verification after deployment;
- explicit rollback semantics for managed configuration;
- public automation that stays separate from private inventories, secrets and recovery evidence.

I do not use it as a scheduler, service mesh, secrets manager, backup engine, deployment database or general-purpose control plane.

## Design

I treat a Git commit as a candidate, not as proof that Production is healthy.

The normal transaction path is:

```text
candidate
   |
   v
preflight + target identity
   |
   v
contract + immutable image checks
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

Configuration rollback and application-data recovery remain separate controls. A stateful stack can require matching recovery-readiness evidence before the configuration transaction is allowed to mutate Production.

The normative semantics are in [`docs/TRANSACTION_MODEL.md`](docs/TRANSACTION_MODEL.md).

## Reference stacks

I keep two stateless reference stacks so the contract is exercised against more than one application shape:

- `stacks/dozzle/`
- `stacks/nginx/`

Each stack owns the same basic structure:

```text
stacks/<name>/
├── compose.yaml
├── defaults.env
├── stack.yml
└── MANIFEST.tsv
```

`stack.yml` defines the target boundary, expected services and functional checks. `MANIFEST.tsv` defines the managed source-to-target file mapping. Remote images are pinned by digest.

## Quick start

My clean-host path on Debian or Ubuntu is:

```bash
git clone https://github.com/d-prost/homelab-ops-blueprint.git
cd homelab-ops-blueprint
bash scripts/setup.sh
```

For dependency installation and repository validation without deploying a reference stack:

```bash
bash scripts/setup.sh --install-only
make validate
```

For the second reference stack:

```bash
bash scripts/setup.sh --stack nginx
```

For another stack already added under `stacks/`:

```bash
bash scripts/setup.sh --stack my-stack
```

Automatic package installation currently targets Debian and Ubuntu. On other Linux distributions I keep the same runtime requirements: Docker Engine with Compose v2, Ansible Core, Python 3 with PyYAML, Git, `sudo`, `tar` and `flock`.

## Production path

I keep Production inventory local and outside the public repository state:

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

My Production transport uses SSH with strict OpenSSH host-key verification. I bind the target to the expected hostname and can optionally pin `/etc/machine-id` as an additional identity check.

My preflight command is:

```bash
bash scripts/deploy-stack.sh dozzle --check
```

My mutation command is:

```bash
bash scripts/deploy-stack.sh dozzle
```

The Production entry point requires a clean `main` matching `origin/main`.

I serialize transactions for the same declared target and stack through a host-global lock on one configured control host. v1 deliberately does not add distributed locking across independent control hosts.

## Stateful services

For a stateful stack I keep recovery evidence separate from Git and provide only the narrow readiness projection consumed by the deployment gate:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/path/to/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<seconds>
```

The evidence is tied to the recovery-relevant stack generation. Configuration rollback never implies application-data rollback.

The format and boundary are documented in [`docs/RECOVERY_READINESS.md`](docs/RECOVERY_READINESS.md).

## Validation

My main local commands are:

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

GitHub Actions runs the corresponding static and disposable proofs. CI validates the repository and transaction behavior; it has no Production deployment authority.

## Repository layout

| Path | Purpose |
|---|---|
| `ansible/` | inventories, playbooks and the managed-stack role |
| `stacks/` | Docker Compose stack contracts and payloads |
| `scripts/` | setup, deployment, rollback and validation helpers |
| `tests/` | unit, contract and disposable transaction proofs |
| `recovery/` | stateful adoption and restore-drill material |
| `advisory/` | public-safe engineering lessons distilled from real operations |
| `docs/` | architecture, adoption, recovery, release and evidence documentation |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Transaction model](docs/TRANSACTION_MODEL.md)
- [Adoption](docs/ADOPTION.md)
- [Evaluation](docs/EVALUATION.md)
- [Recovery readiness](docs/RECOVERY_READINESS.md)
- [Production learning](docs/PRODUCTION_LEARNING.md)
- [Main change controls](docs/MAIN_CHANGE_CONTROLS.md)
- [Real remote SSH proof](docs/REMOTE_SSH_PROOF.md)
- [v1 final acceptance](docs/V1_FINAL_ACCEPTANCE.md)
- [Writing style](docs/WRITING_STYLE.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)

## Project status

I keep support claims narrower than implementation ideas. The single-host stateless transaction path is implemented and exercised by disposable proofs. The remaining first-stable-release gates are the real separate-target SSH evidence and effective GitHub `main` protection described in the v1 acceptance handoff.

Stateful reference recovery, richer deployment records, multi-host rollout and read-only advisory tooling remain separate follow-up work.

## Contributions and feedback

I welcome focused pull requests and reproducible reports. I prefer changes that solve one bounded problem, preserve the transaction model, and include evidence proportional to the behavior being changed.

The contribution baseline is documented in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security

I handle suspected vulnerabilities through GitHub Private Vulnerability Reporting and keep private environment details out of public issues. The full boundary is documented in [`SECURITY.md`](SECURITY.md).

## License

MIT. See [`LICENSE`](LICENSE).
