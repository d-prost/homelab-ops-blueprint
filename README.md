# HomeLab Ops Blueprint

[![Validate blueprint](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml/badge.svg)](https://github.com/d-prost/homelab-ops-blueprint/actions/workflows/validate.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/d-prost/homelab-ops-blueprint/badge)](https://securityscorecards.dev/viewer/?uri=github.com/d-prost/homelab-ops-blueprint)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A public-safe reference project for operating small Docker Compose environments with Git, Ansible, immutable image references, functional verification, and transactional configuration rollback.

The project is intentionally environment-neutral. It is designed to be reusable without publishing real hostnames, IP addresses, credentials, backup metadata, private PKI details, or Production evidence.

## Why this exists

Small self-hosted environments often have enough operational complexity to need disciplined change control, but not enough scale to justify a full orchestration platform. This project focuses on that middle ground:

- reviewed Git as the desired-state source;
- deliberate, manual Production deployment;
- exact host-identity guards;
- immutable container images;
- allowlist-only configuration changes;
- functional health verification instead of trusting `container=running`;
- automatic rollback of previously managed configuration;
- disposable rollback proof in CI;
- explicit separation between public automation and private environment data.

## Safety properties

A Production deployment is refused unless the repository is clean, the current branch is `main`, local `main` exactly matches `origin/main`, a real Production inventory exists locally, and the target hostname exactly matches the inventory declaration.

Managed container images must use `@sha256:` digests. Only files declared by the stack contract may be installed. A deployment record is written only after functional checks pass.

Before replacing an already managed stack, the role captures only the allowlisted managed files in a transient root-owned transaction directory. If deployment or verification fails, it restores the previous files, reapplies the previous Compose model, verifies it again, and removes the transaction directory.

This protects configuration changes. It is not a substitute for application-data backups or restore testing.

## Public/private boundary

The repository must never contain real operational secrets or identifying infrastructure data. Keep these outside Git or in a separate private repository:

- Production hostnames, IP addresses, internal DNS zones, and VPN details;
- passwords, API tokens, private keys, recovery codes, and secret `.env` files;
- real backup receipts, Run IDs, Snapshot IDs, and restore credentials;
- firewall exports, incident logs, private audit evidence, and PKI internals;
- break-glass procedures and private recovery material.

The validation suite includes a public-safety check in addition to Gitleaks. See [`docs/PUBLIC_PRIVATE_BOUNDARY.md`](docs/PUBLIC_PRIVATE_BOUNDARY.md).

## Repository layout

```text
.github/                    CI, Scorecard, Dependabot, issue/PR templates
ansible/                    guarded deployment logic and example inventories
docs/                       architecture, adoption, release, and maintainer docs
recovery/                   generic functional restore-drill template
scripts/                    deployment, validation, and safety tooling
stacks/dozzle/              public stateless example stack
tests/                      integrity and disposable rollback tests
```

## Quick start

### 1. Requirements

- Linux
- Git
- Docker Engine with Compose v2
- Ansible Core
- Python 3 and PyYAML

For the full maintainer validation suite, also install ShellCheck, yamllint, and Gitleaks.

### 2. Validate the repository

The commands deliberately use `bash` and `python3` explicitly, so CI does not depend on executable bits surviving ZIP extraction, browser uploads, or cross-platform Git clients.

```bash
make validate
```

### 3. Create a private Production inventory

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

Edit the ignored `hosts.yml` locally and replace every `CHANGE_ME` value.

### 4. Dry-run the example stack

```bash
bash scripts/deploy-stack.sh dozzle --check
```

### 5. Deploy explicitly

```bash
bash scripts/deploy-stack.sh dozzle
```

### 6. Tag a verified operational release

```bash
bash scripts/tag-release.sh
```

To redeploy an earlier verified operational release:

```bash
bash scripts/rollback-stack.sh dozzle release-YYYYMMDD-HHMMSSZ
```

## CI and supply-chain checks

The validation workflow runs two independent jobs:

- **Static validation**: Bash/Python/YAML checks, stack-contract validation, Ansible syntax checks, public-safety validation, and Gitleaks;
- **Disposable rollback proof**: real Dozzle deployment on a disposable runner, intentional failure injection, automatic configuration rollback, SHA-256 comparison, and functional HTTP verification after rollback.

A separate OpenSSF Scorecard workflow evaluates repository security practices with narrowly scoped permissions. Dependabot watches pinned GitHub Actions for updates.

## Project scope

This project is a deployment-safety blueprint, not a complete HomeLab platform. It deliberately does not provide automatic public-CI Production deployment, secret storage, firewall management, database rollback, or backup orchestration.

See [`ROADMAP.md`](ROADMAP.md) for planned work and explicit non-goals.

## Contributing

Contributions are welcome when they improve safety, portability, testing, documentation, or reusable stack contracts without weakening the public/private boundary.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), [`GOVERNANCE.md`](GOVERNANCE.md), and [`ROADMAP.md`](ROADMAP.md).

## Security

Do not report vulnerabilities containing sensitive infrastructure details in a public issue. Follow [`SECURITY.md`](SECURITY.md).

## Releases

Public project releases use Semantic Versioning. Operational deployment tags created by `scripts/tag-release.sh` are separate from project version tags. See [`docs/RELEASES.md`](docs/RELEASES.md).

## License

MIT. See [`LICENSE`](LICENSE).
