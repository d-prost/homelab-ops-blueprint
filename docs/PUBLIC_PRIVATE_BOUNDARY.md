# Public / Private Boundary

A safe public HomeLab project should publish reusable mechanisms, not a map of the real environment.

## Safe to publish

- generic Ansible roles;
- CI validation;
- deployment guards;
- rollback mechanics;
- generic Compose examples;
- functional health-check implementation;
- recovery-readiness schema and validator;
- synthetic recovery evidence examples;
- restore-drill templates;
- architectural principles.

## Keep private

| Category | Examples |
|---|---|
| Identity | real usernames, hostnames, device names |
| Network | private IP plan, VLAN IDs, internal DNS names, VPN endpoints |
| Access | SSH keys, tokens, credentials, break-glass instructions |
| PKI | private-key locations, signing workflow, internal CA custody details |
| Backup evidence | real repository URLs, Run IDs, Snapshot IDs, receipts |
| Recovery evidence | real readiness projections, restore drill records, restored object identifiers, screenshots |
| Security posture | unresolved firewall holes, exposed admin ports, incident evidence |
| Personal data | document names, media paths that disclose personal information |

The public readiness validator should consume only the minimum projection needed to make a fail-closed decision. It must not require the public repository to store the underlying private backup or restore record.

## Recommended operating model

Use two repositories:

```text
homelab-ops-blueprint     PUBLIC   reusable framework and examples
homelab-env-private       PRIVATE  real inventory, evidence and environment state
```

Do not create the public repository by copying `.git` from the private repository. Start with a fresh Git history.

When using the recovery-readiness gate, keep its real JSON evidence file outside the public repository tree as well. An ignored file inside the public clone is still the wrong trust boundary.
