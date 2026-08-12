# Architecture

## Goal

Keep the public repository useful as an engineering reference while ensuring real Production topology stays private and remote targets do not need repository checkouts.

## Trust boundaries

- **Current control plane:** current `main` inventory, identity guards, playbooks, roles, and verifier.
- **Release payload:** only the selected `stacks/<name>/` directory from `HEAD` or an annotated release.
- **Target Runtime:** Docker, Compose, Python, managed files, persistent data, secrets, and deployment receipts.
- **Git history:** the authoritative prior stack contract used to decide whether configuration rollback is verifiable.

Historical releases never supply executable automation. This prevents an old inventory or old safety logic from becoming authoritative during rollback.

## Control flow

```text
current reviewed Git main
      |
      +--> clean branch / remote equality guard
      +--> current private inventory and exact host guard
      +--> selected stack payload from HEAD or release tag
      |
      v
control-plane preflight
      |
      +--> render Compose model
      +--> require pinned image digests
      +--> validate stack.yml against MANIFEST.tsv
      |
      v
Ansible managed_stack role on target
      |
      +--> read prior deployment receipt
      +--> load exact prior contract from control-plane Git history
      +--> stage candidate files and contract
      +--> capture prior allowlisted files transiently
      +--> atomically install candidate files
      +--> docker compose up -d
      +--> expected-service check
      +--> transferred verifier + staged contract
      |
      +--> success: deployment receipt
      |
      +--> failure: remove candidate-only files
                     -> restore prior files
                     -> reapply prior Compose model
                     -> verify with prior contract
                     -> fail closed
```

The split between control-plane rendering and target Runtime verification is intentional. A local Ansible connection can hide incorrect path assumptions; at least one bounded real remote deployment is required before claiming remote support.

## Stateful boundary

Transactional deployment protects sanitized configuration files only. Databases, media, indexes, uploads, named volumes, application-generated state, and secrets remain outside that rollback transaction. Their protection requires application-aware exports, backups, isolated restore drills, and functional proof described in [the stateful adoption checklist](../recovery/STATEFUL_ADOPTION_CHECKLIST.md).

## Deliberate exclusions

- no automatic Production deployment from CI;
- no stateful database migration automation;
- no backup writer;
- no secret store implementation;
- no firewall management;
- no private infrastructure inventory.

Those belong to environment-specific private operations.
