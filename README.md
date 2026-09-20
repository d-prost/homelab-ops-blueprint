# HomeLab Ops Blueprint

A small Git + Ansible workflow for deploying Docker Compose stacks without adding a full orchestration platform.

[![Validate blueprint](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml/badge.svg)](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/d-prost/homelab-ops-blueprint/badge)](https://securityscorecards.dev/viewer/?uri=github.com/d-prost/homelab-ops-blueprint)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

I built this for homelab-sized environments where `docker compose up -d` is easy, but making changes safely and rolling them back is not. Git holds the stack definition, Ansible applies it, and the target is checked before a deployment is considered successful.

The current implementation is aimed at single-host Docker Compose setups. `stacks/dozzle/` and `stacks/nginx/` are stateless reference stacks that exercise the same deployment contract with different applications.

## Who this is for

This project is intended for operators who:

- run one or a small number of Linux hosts with Docker Compose;
- want Git-reviewed, reproducible changes without adopting Kubernetes or another full orchestration platform;
- care about validating the target before a change, checking the application after it starts, and having an explicit configuration rollback path;
- want public-safe automation that can be adapted to a private environment without publishing private inventories, secrets, backup locations or recovery evidence.

It is not intended to be a general-purpose scheduler, service mesh, secrets manager or replacement for application-aware backup and restore tooling.

## What makes the workflow different

The deployment path treats a Git commit as a candidate, not as proof that Production is healthy. Before a candidate is accepted, the workflow checks the repository state, target identity, stack contract, immutable image references and functional checks on the target. If a managed configuration change fails and the previous accepted configuration can be reconstructed, the deployment path restores that configuration and verifies it again.

Configuration rollback and persistent application-data recovery deliberately remain separate mechanisms. Stateful services can require independent recovery-readiness evidence before a Production mutation is allowed.

## Project maturity

The project is actively maintained and currently pre-1.0. The single-host stateless deployment path, contract validation, immutable image enforcement, functional verification and disposable rollback proof are implemented. Recovery-readiness gating for stateful stacks is also implemented.

Before the first stable release, the project still needs more real-world remote-host validation and deeper parser/failure-path coverage. The current scope and remaining work are tracked in [`ROADMAP.md`](ROADMAP.md).

## Quick start

On a fresh Debian or Ubuntu host, clone the repository and run the setup script:

```bash
git clone https://github.com/d-prost/homelab-ops-blueprint.git
cd homelab-ops-blueprint
bash scripts/setup.sh
```

The setup script installs the required runtime packages, starts Docker, validates the repository and deploys the Dozzle reference stack locally. It installs Docker Engine with Compose v2 when needed, Ansible Core, Python/PyYAML and the other packages required by the deployment scripts.

To install the dependencies and validate the checkout without deploying a reference stack:

```bash
bash scripts/setup.sh --install-only
make validate
```

To deploy the second reference stack instead:

```bash
bash scripts/setup.sh --stack nginx
```

To use another stack after adding it to `stacks/`:

```bash
bash scripts/setup.sh --stack my-stack
```

Automatic package installation currently supports Debian and Ubuntu. On another Linux distribution, install Docker Engine with Compose v2, Ansible Core, Python 3 with PyYAML, Git, `sudo`, `tar` and `flock`, then use the normal deployment commands below.

## Production setup

For a Production host, install the dependencies first without starting the Lab example:

```bash
bash scripts/setup.sh --install-only
```

Create the local Production inventory:

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

Edit `hosts.yml` and replace the example values with the real SSH target settings. Production uses strict OpenSSH host-key verification; add the trusted target key to the operator's normal `known_hosts` file before running the deployment. Unknown or changed host keys are refused.

The hostname is mandatory. `homelab_expected_machine_id` is optional and may remain `null`; when set, the target's `/etc/machine-id` must also match before mutation.

Preview the deployment:

```bash
bash scripts/deploy-stack.sh dozzle --check
```

Deploy it:

```bash
bash scripts/deploy-stack.sh dozzle
```

The Production entry point expects a clean `main` that matches `origin/main`.

## What happens during a deployment

Before Production is changed, the deployment path verifies that:

- the local checkout is a clean, up-to-date `main`;
- the Production transport is SSH with host-key checking enabled;
- the selected inventory host matches the target hostname;
- the optional pinned `/etc/machine-id` matches when configured;
- the exact selected stack payload passes the current contract validator;
- each stack declares the files it manages and the services it expects;
- `MANIFEST.tsv` matches the source-to-target file mapping;
- container images are pinned by digest;
- functional checks pass on the target after Compose starts;
- the accepted Git commit is recorded only after those checks pass.

Files that were managed by the previous release but are no longer part of the new contract are removed. Compose is also run with orphan cleanup so removed services do not remain running after a successful deployment or rollback.

If a deployment fails and the previous managed configuration can be reconstructed, the role restores that configuration and runs the previous checks again. This rollback covers managed configuration, not application data or Docker volumes.

Stateful stacks can also require recovery-readiness evidence before a Production change. That is handled separately from configuration rollback; see [`docs/RECOVERY_READINESS.md`](docs/RECOVERY_READINESS.md).

## Stack layout

Each stack is self-contained:

```text
stacks/<name>/
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

Historical releases provide the stack payload only. The current checkout still supplies inventory, validation and deployment logic. Production release tags are checked against `origin`, and the selected release commit must belong to `origin/main` history.

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

Local validation does not require the optional lint/security tools. CI installs ShellCheck, yamllint and Gitleaks and runs the stricter checks automatically.

GitHub Actions runs static validation and a disposable rollback test. The rollback workflow deploys the Dozzle example, introduces a failure, restores the previous configuration and verifies the service again.

For a short reviewer/adopter path that does not touch an existing Production environment, see [`docs/EVALUATION.md`](docs/EVALUATION.md).

## Repository layout

| Path | Contents |
|---|---|
| `ansible/` | inventories, playbooks and the managed-stack role |
| `stacks/` | Docker Compose stack definitions |
| `scripts/` | setup, deploy, rollback, validation and readiness helpers |
| `tests/` | contract, readiness and rollback tests |
| `recovery/` | stateful adoption and restore-drill templates |
| `docs/` | architecture, setup, recovery and release notes |

## Documentation

- [`docs/EVALUATION.md`](docs/EVALUATION.md) — reproducible reviewer/adopter evaluation path
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the deployment and rollback path is put together
- [`docs/ADOPTION.md`](docs/ADOPTION.md) — adapting the repository to your own stacks
- [`docs/RECOVERY_READINESS.md`](docs/RECOVERY_READINESS.md) — stateful readiness checks and evidence format
- [`docs/RELEASES.md`](docs/RELEASES.md) — project releases and operational tags
- [`ROADMAP.md`](ROADMAP.md) — planned work and stable-release criteria
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — development and pull-request notes

## Project status

The single-host stateless deployment path and disposable rollback test are implemented, with Dozzle and Nginx as separate public reference stacks. Remote targets work without a Git checkout on the target, although the project still needs more real-world remote-host coverage. Stateful readiness support is in place, while richer stateful declarations, a complete synthetic stateful example and multi-host deployment are still planned.

The project is intentionally conservative about claims of support: functionality moves out of the roadmap only after it has a reproducible proof or enough real-world coverage to justify the claim.

## Contributing and feedback

Run `make validate` before opening a pull request. If a change affects deployment or rollback behavior, run `make lab-proof` as well.

External deployment reports are useful even when no code change is needed. If you try the blueprint on a disposable or non-critical host, open a GitHub Discussion or Issue with the Linux distribution, Docker/Compose version, whether the target was local or remote, and the smallest reproducible details for anything that failed. Do not include credentials, private hostnames, addresses or recovery evidence.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## Security

Please report security issues through GitHub Private Vulnerability Reporting. See [`SECURITY.md`](SECURITY.md).

## License

MIT. See [`LICENSE`](LICENSE).
