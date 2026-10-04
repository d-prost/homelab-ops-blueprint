# Security Policy

## Supported versions

I apply security fixes to the default branch and, once public releases exist, to the latest supported major release.

## Vulnerability reports

I handle suspected vulnerabilities through GitHub Private Vulnerability Reporting in the repository **Security** tab.

I keep exploit details, credentials, private hostnames, internal addresses, private URLs, backup metadata, private keys and recovery material out of public issues.

If private vulnerability reporting is unavailable, a public issue should contain only enough non-sensitive information to establish a private reporting channel.

Non-sensitive hardening suggestions can use the normal issue tracker.

## Response targets

These are working targets, not contractual SLAs:

- private report acknowledged within 7 days;
- initial assessment within 14 days when reasonably possible;
- disclosure coordinated after a fix or mitigation exists;
- exploit details withheld until there has been a reasonable opportunity to update.

A useful private report identifies the affected component, expected security impact, reproducible details and any proposed mitigation.

## Security boundary

I keep reusable deployment logic in this repository and keep real Production inventory and secrets outside it.

The project covers guarded configuration changes. Host hardening, network access control, secret storage, backup execution, functional restore testing and monitoring remain separate responsibilities in my environment.

Configuration rollback is not data recovery.

## Secret exposure

I treat a committed secret as compromised. My recovery order is rotation or revocation first, repository cleanup second, and history rewriting when the exposure requires it.

Deleting the current file does not invalidate material already exposed through commits, forks, caches or logs.
