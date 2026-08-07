# Security Policy

## Supported versions

Security fixes are applied to the default branch and to the latest released major version once public releases exist.

## Reporting a vulnerability

Please use GitHub Private Vulnerability Reporting from the repository's **Security** tab for suspected vulnerabilities.

Do not open a public issue containing exploit details, credentials, private hostnames, internal IP addresses, private URLs, backup metadata, private keys, recovery material, or information that could expose a real environment.

If private vulnerability reporting is temporarily unavailable, open only a minimal non-sensitive issue asking for a private reporting channel. Do not include vulnerability details in that issue.

For non-sensitive hardening suggestions, a normal GitHub issue is appropriate.

## Response and disclosure targets

These are response targets rather than contractual SLAs:

- acknowledge a private report within 7 days;
- provide an initial assessment within 14 days when reasonably possible;
- coordinate disclosure with the reporter after a fix or mitigation is available;
- avoid publishing exploit details before users have had a reasonable opportunity to update.

A valid report should include the affected component or workflow, expected security impact, reproduction details that are safe to share privately, and any suggested mitigation.

## Project security boundary

This repository intentionally contains reusable deployment logic but no real Production inventory or secrets. Consumers are responsible for host hardening, network access control, secret storage, backups, functional restore testing, and monitoring.

Configuration rollback is not data recovery.

## If a secret is committed

Assume it is compromised. Rotate or revoke it first, then remove it from the repository and, when necessary, rewrite affected Git history. Deleting the current file alone does not invalidate material already exposed in commits, forks, caches, or logs.
