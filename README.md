# HomeLab Ops Blueprint

A public-safe reference implementation for operating a small Docker Compose HomeLab with Git, Ansible, immutable image references, functional health checks, and transactional configuration rollback.

This repository is intentionally environment-neutral. It contains no real production inventory, IP addresses, credentials, backup receipts, certificate paths, recovery codes, or private infrastructure evidence.

## What this project demonstrates

- manual Production deployment from reviewed Git only;
- clean-branch and exact `main == origin/main` guards;
- private Production inventory kept outside Git;
- explicit host identity checks before any deployment;
- immutable container image references using `@sha256:` digests;
- allowlist-only managed files;
- transient transaction rollback without persistent `.bak` files;
- functional HTTP verification after deploy and after rollback;
- an ephemeral Lab rollback proof in GitHub Actions;
- complete-history secret scanning with Gitleaks;
- a practical functional restore-drill template.

## Public/private boundary

The public repository contains reusable logic and examples. Real environment data belongs in ignored local files or a separate private repository.

Never commit:

- real Production hostnames, IP addresses or internal DNS zones;
- passwords, tokens, API keys, private keys or recovery codes;
- `.env` files containing secrets;
- real backup Run IDs, Snapshot IDs or receipts;
- firewall exports, private audit evidence or incident logs;
- private PKI layout or break-glass procedures.

See [`docs/PUBLIC_PRIVATE_BOUNDARY.md`](docs/PUBLIC_PRIVATE_BOUNDARY.md).

## Repository layout

```text
.github/workflows/       CI validation and Lab rollback proof
ansible/                 guarded deployment logic
scripts/                 operator commands and validation
stacks/dozzle/           public stateless example stack
recovery/                generic restore-drill template
docs/                    architecture and adoption guidance
tests/                   integrity and rollback tests
```

## Requirements

Controller:

- Linux
- Git
- Docker Engine with Compose v2
- Ansible Core
- Python 3 + PyYAML
- ShellCheck
- yamllint
- Gitleaks

Production deployment is deliberately local/manual. CI validates the desired state but does not deploy Production.

## Quick start

### 1. Clone

```bash
git clone <your-public-repository-url>
cd homelab-ops-blueprint
```

### 2. Validate

```bash
scripts/validate-repository.sh
```

### 3. Create a private Production inventory

The real file is ignored by Git:

```bash
cp ansible/inventory/production/hosts.example.yml \
   ansible/inventory/production/hosts.yml
```

Edit `hosts.yml` locally and replace every `CHANGE_ME` value.

### 4. Dry-run a stack

```bash
scripts/deploy-stack.sh dozzle --check
```

Production deployment is refused unless:

- the repository is clean;
- the current branch is `main`;
- local `main` exactly equals `origin/main`;
- the Production inventory resolves to at least one host;
- the actual hostname exactly matches `homelab_expected_hostname`.

### 5. Deploy explicitly

```bash
scripts/deploy-stack.sh dozzle
```

A successful deployment writes a non-secret deployment record only after the functional health check passes.

## Transaction rollback

Before replacing an already managed stack, Ansible copies only the allowlisted managed configuration files into a transient root-owned directory. If Compose application, service-state verification, or functional verification fails, the role restores the previous managed files, reapplies the previous Compose model, verifies it again, and reports the failed deployment.

The transaction directory is removed afterward. It is not an accumulating backup archive.

A first adoption has no prior managed configuration and therefore no automatic rollback target. Test first adoption in Lab before relying on Production automation.

## Release rollback

After a verified Production deployment:

```bash
scripts/tag-release.sh
```

To redeploy an earlier verified release:

```bash
scripts/rollback-stack.sh dozzle release-YYYYMMDD-HHMMSSZ
```

Configuration rollback is not data recovery. Databases and application data require their own restore procedures.

## CI

GitHub Actions performs:

- Bash, YAML and Python validation;
- stack-contract validation;
- Ansible syntax checks;
- Gitleaks scan of complete Git history;
- real disposable Dozzle deployment;
- intentional replacement failure;
- automatic rollback;
- managed-file SHA-256 comparison;
- functional HTTP verification after rollback.

## Security model

This project reduces deployment mistakes. It is not a complete security platform and does not replace host hardening, network controls, secret management, backups, restore testing, or monitoring.

Read [`SECURITY.md`](SECURITY.md) before adapting it to a real environment.

## License

MIT. See [`LICENSE`](LICENSE).
