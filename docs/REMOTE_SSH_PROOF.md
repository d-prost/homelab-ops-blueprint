# Real remote SSH proof

This runbook prepares and records the v1 remote-target proof required by issue #35.

It does **not** count as proof by itself. The issue is complete only after the
steps are executed against a genuinely separate disposable or non-critical SSH
target and the resulting public-safe evidence is recorded.

## Boundary

The proof target must be separate from the control host.

Use a disposable or non-critical target only. Do not use a production service
whose availability or data matters to you.

The proof must exercise:

1. verified SSH transport identity;
2. declared target hostname identity;
3. candidate deployment;
4. functional verification;
5. durable accepted evidence;
6. a deliberately failing candidate;
7. verified restoration of the previous accepted managed configuration.

The public evidence must not contain:

- private hostnames;
- IP addresses;
- usernames;
- SSH keys or known-hosts contents;
- credentials;
- deployment records;
- backup or recovery identifiers.

## 1. Prepare the remote target

The remote target needs:

- Debian or Ubuntu;
- Python 3;
- Docker Engine;
- Docker Compose v2;
- an SSH account that can use `sudo` for the proof.

The control host needs the normal project dependencies and a clean checkout of
the current `main`.

Create a private inventory file outside the repository, for example:

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

Add the trusted target SSH host key to the operator's normal `known_hosts`
file before continuing. Do not use `StrictHostKeyChecking=no`,
`accept-new`, or `UserKnownHostsFile=/dev/null`.

## 2. Prove transport and target readiness

Run:

```bash
HOMELAB_REMOTE_PROOF=1 \
  bash scripts/collect-remote-proof-facts.sh /absolute/path/to/private-hosts.yml
```

The helper validates that the inventory resolves to exactly one remote SSH
target classified as `lab`, runs the repository target-identity preflight, and
prints only public-safe environment facts.

Store the output locally. Do not commit private inventory or raw Ansible output.

## 3. Baseline candidate

Use the current Dozzle reference stack as the baseline.

The remote proof intentionally uses the same deployment playbook and
`managed_stack` role as the normal transaction path. It must not replace the
Production authorization wrapper or weaken its clean-main requirements.

Record:

- candidate commit;
- transaction result;
- functional verification result;
- that an accepted record exists on the target.

Do not publish the accepted record itself.

## 4. Inject a failing candidate

The failure fixture must be built outside the tracked checkout and must keep all
images digest-pinned. A suitable fixture changes only the disposable Dozzle
Compose payload so the container exits immediately.

Run that fixture through the same deployment playbook against the same remote
target while supplying the frozen previous accepted payload and record identity.

Expected terminal result:

```text
REJECTED_ROLLBACK_VERIFIED
```

The proof is invalid if it only checks container state. It must show that the
previous accepted functional checks pass again after restoration.

## 5. Cleanup

After collecting evidence:

- stop and remove the disposable reference stack;
- remove the project-managed target directory;
- remove the proof deployment/transaction records from the disposable target;
- keep private SSH material and inventory outside the repository.

## 6. Public evidence record

Copy `docs/evidence/REMOTE_SSH_PROOF_TEMPLATE.md` to a new evidence document
only after a real run.

The evidence record should contain:

- date;
- repository commit tested;
- OS distribution/version;
- Docker Engine version;
- Docker Compose version;
- Ansible Core version;
- topology class: `separate SSH target`;
- baseline deployment result;
- injected-failure result;
- rollback functional re-verification result;
- relevant non-sensitive elapsed timings;
- any reproducible compatibility issue discovered.

Do not mark issue #35 complete from documentation or CI alone. A separate SSH
target must actually be exercised.
