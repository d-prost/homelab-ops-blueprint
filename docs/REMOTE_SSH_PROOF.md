# Real remote SSH proof

This is the real separate-target proof I use for issue #35.

Documentation and simulated SSH do not count as completion. I only close the proof after I run the transaction against a genuinely separate disposable or non-critical SSH target and record public-safe evidence.

## Boundary

I keep the proof target separate from the control host and away from workloads whose availability or data matters.

The proof covers:

1. verified SSH transport identity;
2. declared target hostname identity;
3. candidate deployment;
4. functional verification;
5. durable accepted evidence;
6. deliberate candidate failure;
7. restoration of the previous accepted managed configuration;
8. functional re-verification after restoration.

I keep private hostnames, addresses, usernames, SSH material, credentials, deployment records and recovery identifiers out of the public evidence.

## Target shape

My remote proof target provides:

- Debian or Ubuntu;
- Python 3;
- Docker Engine;
- Docker Compose v2;
- an SSH account with the required `sudo` capability.

My control host uses the normal project dependencies and a clean current `main`.

I keep the proof inventory outside the repository:

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

The target key exists in my normal `known_hosts` trust store. I do not weaken host-key verification with `StrictHostKeyChecking=no`, `accept-new` or `UserKnownHostsFile=/dev/null`.

## Public-safe facts

My fact collection command is:

```bash
HOMELAB_REMOTE_PROOF=1 \
  bash scripts/collect-remote-proof-facts.sh /absolute/path/to/private-hosts.yml
```

The helper proves one remote SSH target classified as `lab`, runs target identity preflight and prints only the public-safe environment facts I need for the evidence record.

Raw inventory and raw Ansible output stay private.

## Healthy baseline

I use the current Dozzle reference stack as the baseline.

The proof uses the same deployment playbook and `managed_stack` role as the normal transaction path.

I record:

- candidate commit;
- transaction result;
- functional verification result;
- existence of durable accepted evidence.

I do not publish the accepted record itself.

## Failing candidate

I build the failure fixture outside the tracked checkout and keep all images digest-pinned.

The fixture changes only the disposable Dozzle payload enough to make the container exit immediately.

I run that candidate against the same remote target with the frozen previous accepted payload and record identity.

The terminal result I require is:

```text
REJECTED_ROLLBACK_VERIFIED
```

Container state alone is not sufficient. I require the previous accepted functional checks to pass again after restoration.

## Cleanup

After collecting evidence I remove:

- the disposable reference stack;
- the project-managed target directory;
- proof deployment and transaction records from the disposable target.

Private SSH material and inventory remain outside the repository.

## Public evidence record

After the real run I create a dated evidence document from:

```text
docs/evidence/REMOTE_SSH_PROOF_TEMPLATE.md
```

The public record contains:

- date;
- repository commit;
- OS distribution/version;
- Docker Engine version;
- Docker Compose version;
- Ansible Core version;
- topology class: `separate SSH target`;
- baseline result;
- injected-failure result;
- rollback functional re-verification result;
- relevant non-sensitive timings;
- any reproducible compatibility issue.

I only close #35 after this real separate-target evidence exists in Git.
