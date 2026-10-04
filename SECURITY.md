# Security Policy

## Supported versions

Security fixes are applied to the default branch and, once public releases exist, to the latest supported major release.

## Reporting a vulnerability

Use GitHub Private Vulnerability Reporting from the repository **Security** tab for suspected vulnerabilities.

Public issues should not contain exploit details, credentials, private hostnames, internal addresses, private URLs, backup metadata, private keys or recovery material.

If private reporting is unavailable, a public issue can be used only to establish a private reporting channel without including vulnerability details.

Non-sensitive hardening suggestions can use the normal issue tracker.

## Response targets

These are working targets rather than contractual SLAs:

- acknowledgement within 7 days;
- initial assessment within 14 days when reasonably possible;
- coordinated disclosure after a fix or mitigation exists;
- exploit details withheld until there has been a reasonable opportunity to update.

## Project boundary

The repository contains reusable deployment logic, not real Production inventory or secrets.

Host hardening, network access control, secret storage, backup execution, restore testing and monitoring remain separate operational responsibilities.

Configuration rollback is not data recovery.

## Secret exposure

A committed secret should be treated as compromised: rotate or revoke it first, then remove it from the repository and rewrite history if the exposure requires it.

Deleting the current file alone does not invalidate material already present in commits, forks, caches or logs.
