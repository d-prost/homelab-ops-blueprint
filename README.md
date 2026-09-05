# HomeLab Ops Blueprint

A small Git + Ansible workflow for deploying Docker Compose stacks without adding a full orchestration platform.

[![Validate blueprint](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml/badge.svg)](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/d-prost/homelab-ops-blueprint/badge)](https://securityscorecards.dev/viewer/?uri=github.com/d-prost/homelab-ops-blueprint)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

I built this for homelab-sized environments where `docker compose up -d` is easy, but making changes safely and rolling them back is not. The repository keeps the deployment path deliberately simple: Git holds the stack definition, Ansible applies it, and the target is checked before a deployment is considered successful.

The current implementation is aimed at single-host Docker Compose setups. `stacks/dozzle/` is the reference stack.

## What it does

A Production deployment goes through a few checks before anything is changed:

- the local checkout must be a clean, up-to-date `main`;
- the selected inventory host must match the target hostname;
- each stack declares the files it manages and the services it expects;
- `MANIFEST.tsv` must match the source-to-target file mapping;
- container images are pinned by digest;
- functional checks run on the target after Compose starts;
- the accepted Git commit is recorded only after those checks pass.

If a deployment fails and the previous managed configuration can be reconstructed, the role restores that configuration and runs the previous checks again. This rollback covers managed configuration, not application data or Docker volumes.

Stateful stacks can also require recovery-readiness evidence before a Production change. That is handled separately from configuration rollback; see [`docs/RECOVERY_READINESS.md`](docs/RECOVERY_READINESS.md).

## Quick start

### Requirements

- Linux
- Git
- Docker Engine with Compose v2
- Ansible Core
- Python 3 with PyYAML

For the full validation suite, install ShellCheck, yamllint and Gitleaks as well.

### Validate the repository

```bash
make validate
```

### Configure a Production host

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

Edit `hosts.yml` and replace the example values with your host settings.

### Preview a deployment

```bash
bash scripts/deploy-stack.sh dozzle --check
```

### Deploy

```bash
bash scripts/deploy-stack.sh dozzle
```

The Production entry point expects a clean `main` that matches `origin/main`.

## Stack layout

Each stack is self-contained:

```text
stacks/dozzle/
├── compose.yaml
├── defaults.env
├── stack.yml
└── MANIFEST.tsv
```

`stack.yml` describes the target directory, managed files, expected services and functional checks. `MANIFEST.tsv` maps repository files to their target paths. The deployment role stages and installs only the files declared by that contract.

A minimal deployment flow looks like this:

```mermaid
flowchart LR
    A[Git commit] --> B[Preflight]
    B --> C[Validate stack]
    C --> D[Check target]
    D --> E[Deploy files + Compose]
    E --> F[Run target checks]
    F -->|pass| G[Record accepted state]
    F -->|fail| H[Restore previous config]
    H --> I[Run previous checks]
```

## Releases and rollback

Create an operational release tag with:

```bash
bash scripts/tag-release.sh
```

To deploy an earlier tagged stack payload:

```bash
bash scripts/rollback-stack.sh dozzle release-YYYYMMDD-HHMMSSZ
```

Historical releases provide the stack payload only. Deployment logic, inventory and validation continue to come from the current checkout, so an old tag cannot silently replace newer deployment guards.

Automatic rollback is intentionally limited to configuration that was managed by this project and can be reconstructed from the previous accepted state. Database contents, uploads, media, indexes and other persistent application data need their own backup and restore process.

## Stateful stacks

A stack can declare stateful services in `stack.yml`. For Production, the deployment path can require a recovery-readiness file and a backup-age policy:

```bash
export HOMELAB_RECOVERY_EVIDENCE=/path/to/recovery-readiness.json
export HOMELAB_BACKUP_MAX_AGE_SECONDS=<seconds>
```

The readiness check verifies that the evidence applies to the current stack generation before the deployment proceeds. The schema and hash calculation are documented in [`docs/RECOVERY_READINESS.md`](docs/RECOVERY_READINESS.md).

## Validation

The main local commands are:

```bash
make validate     # syntax, contracts, tests and repository checks
make lab-proof    # disposable deployment, injected failure and rollback test
make ci           # CI-oriented validation including Gitleaks when available
```

GitHub Actions runs static validation and a disposable rollback test. The rollback workflow deploys the Dozzle example, introduces a failure, restores the previous configuration and verifies the service again.

## Repository layout

| Path | Contents |
|---|---|
| `ansible/` | inventories, playbooks and the managed-stack role |
| `stacks/` | Docker Compose stack definitions |
| `scripts/` | deploy, rollback, validation and readiness helpers |
| `tests/` | contract, readiness and rollback tests |
| `recovery/` | stateful adoption and restore-drill templates |
| `docs/` | architecture, setup, recovery and release notes |

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the deployment and rollback path is put together
- [`docs/ADOPTION.md`](docs/ADOPTION.md) — adapting the repository to your own stacks
- [`docs/RECOVERY_READINESS.md`](docs/RECOVERY_READINESS.md) — stateful readiness checks and evidence format
- [`docs/RELEASES.md`](docs/RELEASES.md) — project releases and operational tags
- [`ROADMAP.md`](ROADMAP.md) — planned work
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — development and pull-request notes

## Project status

The single-host stateless deployment path and disposable rollback test are implemented. Remote targets work without a Git checkout on the target, although the project still needs more real-world remote-host coverage. Stateful readiness support is in place, while richer stateful declarations, a complete synthetic stateful example and multi-host deployment are still planned.

## Contributing

Run `make validate` before opening a pull request. If a change affects deployment or rollback behavior, run `make lab-proof` as well.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## Security

Please report security issues through GitHub Private Vulnerability Reporting. See [`SECURITY.md`](SECURITY.md).

## License

MIT. See [`LICENSE`](LICENSE).
