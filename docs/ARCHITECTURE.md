# Architecture

## Goal

Keep the public repository useful as engineering reference while ensuring real Production topology stays private.

## Control flow

```text
reviewed Git main
      |
      v
operator invokes deploy-stack.sh
      |
      +--> Git cleanliness / branch / remote equality guard
      +--> private inventory host-count guard
      +--> exact hostname guard
      +--> preflight Compose + digest validation
      |
      v
Ansible managed_stack role
      |
      +--> candidate render
      +--> transient previous-config capture
      +--> atomic allowlisted file install
      +--> docker compose up -d
      +--> expected-service check
      +--> functional HTTP check
      |
      +--> success: deployment record
      |
      +--> failure: restore previous files -> reapply -> verify -> fail closed
```

## Deliberate exclusions

- no automatic Production deployment from CI;
- no stateful database migration automation;
- no backup writer;
- no secret store implementation;
- no firewall management;
- no private infrastructure inventory.

Those belong to environment-specific private operations.
