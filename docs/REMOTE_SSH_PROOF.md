# Real remote SSH proof

Issue #35 requires one end-to-end transaction proof against a genuinely separate SSH target.

Documentation or simulated transport does not satisfy the proof.

## Boundary

The target must be disposable or non-critical and separate from the control host.

The proof covers:

1. verified SSH transport identity;
2. declared target hostname identity;
3. candidate deployment;
4. functional verification;
5. durable acceptance;
6. deliberate candidate failure;
7. restoration of the previous accepted configuration;
8. functional re-verification after restoration.

Public evidence must not contain private hostnames, addresses, usernames, SSH material, credentials, deployment records or recovery identifiers.

## Target requirements

The target needs:

- Debian or Ubuntu;
- Python 3;
- Docker Engine;
- Docker Compose v2;
- an SSH account with the required `sudo` capability.

The control host uses the normal project dependencies and a clean current `main`.

Example private inventory:

```yaml
---
all:
  hosts:
    proof-target:
      ansible_connection: ssh
      ansible_host: <private-address>
      ansible_user: <private-user>
      homelab_environment: lab
      homelab_expected_hostname: <exact-target-hostname>
      homelab_expected_machine_id: null
```

The target SSH key must already exist in the normal `known_hosts` trust store. Host-key verification is not weakened for the proof.

## Public-safe facts

```bash
HOMELAB_REMOTE_PROOF=1 \
  bash scripts/collect-remote-proof-facts.sh /absolute/path/to/private-hosts.yml
```

The helper resolves one remote SSH target classified as `lab`, runs target-identity preflight and prints only the non-sensitive environment facts used by the evidence record.

Raw inventory and raw Ansible output remain private.

## Healthy baseline

The current Dozzle reference stack is used as the baseline.

Record:

- candidate commit;
- transaction result;
- functional verification result;
- existence of durable accepted evidence.

The accepted record itself is not published.

## Failing candidate

The failure fixture stays outside the tracked checkout and keeps images digest-pinned.

The expected terminal result is:

```text
REJECTED_ROLLBACK_VERIFIED
```

Container state alone is not sufficient; the previous functional checks must pass again after restoration.

## Cleanup

Remove the disposable stack, project-managed target directory and proof transaction records from the test target after evidence collection.

Private SSH material and inventory remain outside the repository.

## Public evidence

A dated evidence record is created from:

```text
docs/evidence/REMOTE_SSH_PROOF_TEMPLATE.md
```

The public record includes:

- date;
- repository commit;
- OS distribution/version;
- Docker Engine version;
- Docker Compose version;
- Ansible Core version;
- topology class: `separate SSH target`;
- baseline result;
- injected-failure result;
- rollback re-verification result;
- relevant non-sensitive timings;
- reproducible compatibility issues, if any.

Issue #35 closes only after the real separate-target evidence exists in Git.
