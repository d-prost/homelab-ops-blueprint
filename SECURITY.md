# Security Policy

## Scope

This repository is a reusable blueprint. Do not report vulnerabilities in your private HomeLab configuration by opening a public issue here.

## Never publish environment secrets

Do not commit or paste into issues, pull requests, CI logs, screenshots or examples:

- credentials, tokens, API keys or recovery codes;
- SSH or TLS private keys;
- Restic passwords or remote credentials;
- complete environment files;
- real private IP plans or internal host inventories;
- sensitive backup receipts, snapshot identifiers or recovery packs;
- incident evidence that exposes private infrastructure.

If a secret is committed, assume it is compromised. Rotate it first. Removing the current file does not remove it from Git history.

## Deployment assumptions

The blueprint assumes:

- Production is not automatically deployed from GitHub Actions;
- administrative services are restricted to trusted networks or VPN access;
- Docker and sudo access are already protected;
- Production secrets live outside this public repository;
- stateful services have independent backup and restore procedures.

## Reporting a vulnerability

Use GitHub private vulnerability reporting if enabled by the repository owner. Otherwise contact the maintainer through a private channel rather than disclosing exploitable details publicly.
