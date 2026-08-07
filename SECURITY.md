# Security Policy

## Supported versions

Security fixes are applied to the default branch and the latest released major version once public releases exist.

## Reporting a vulnerability

Use GitHub Private Vulnerability Reporting when it is enabled for this repository.

Do not open a public issue containing credentials, private hostnames, internal IP addresses, private URLs, backup metadata, private keys, recovery material, or exploit details against a real environment.

For non-sensitive hardening suggestions, a normal GitHub issue is appropriate.

## Project security boundary

This repository intentionally contains reusable deployment logic but no real Production inventory or secrets. Consumers are responsible for host hardening, network access control, secret storage, backups, functional restore testing, and monitoring.

Configuration rollback is not data recovery.

## If a secret is committed

Assume it is compromised. Rotate or revoke it first, then remove it from the repository and, when necessary, rewrite affected Git history. Deleting the current file alone does not invalidate material already exposed in commits, forks, caches, or logs.
