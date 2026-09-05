# Architecture

This repository uses Git as the source for stack definitions and Ansible as the deployment mechanism. The important rule is simple: starting containers is not enough to call a deployment successful. The target has to match the selected host, the stack contract has to be valid, and the service checks have to pass.

## Main pieces

### Git checkout

The current checkout provides the deployment code, inventory, validation scripts and stack definitions. Production runs require a clean `main` that matches `origin/main`.

Operational release tags are used when an older stack payload needs to be deployed. Only the selected `stacks/<name>/` payload comes from the tag; the current checkout still provides Ansible, inventory and validation logic.

### Inventory

The Production inventory selects the target and declares the hostname expected on that machine. Preflight compares the declared name with the hostname returned by the target before deployment starts.

### Stack contract

Each stack contains:

```text
stacks/<name>/
├── compose.yaml
├── defaults.env
├── stack.yml
└── MANIFEST.tsv
```

`stack.yml` describes the target directory, files managed by the deployment, expected Compose services and functional checks. `MANIFEST.tsv` provides the source-to-target mapping for the managed files.

The role validates both before copying anything. Images referenced by managed Compose files must be pinned with `@sha256:` digests.

### Target

The target needs Docker, Docker Compose and Python. It does not need a checkout of this repository. Ansible transfers the files and verifier needed for the deployment.

## Deployment flow

The normal Production path is `scripts/deploy-stack.sh`.

```text
operator
  |
  v
check local Git state
  |
  v
load inventory + selected stack
  |
  v
validate target hostname, contract and image digests
  |
  +--> stateful stack: run recovery-readiness check
  |
  v
stage managed files
  |
  v
capture previous managed configuration when rollback is possible
  |
  v
install candidate files
  |
  v
docker compose up -d
  |
  v
verify expected services + functional checks on the target
  |
  +--> success: write deployment record
  |
  +--> failure: restore previous managed configuration and verify it again
```

The deployment entry point also uses a non-blocking `flock` lock so two Production changes cannot run at the same time.

## Why the current checkout stays in control

A rollback or historical deployment may need an older Compose file, but it should not bring back old automation around it. For that reason, release tags are treated as payload sources rather than complete copies of the control plane.

This means an older tag cannot replace:

- the current inventory;
- hostname checks;
- Ansible roles and playbooks;
- validation scripts;
- functional verification code;
- stateful readiness checks.

The same rule also prevents an old payload from bypassing a stateful classification that exists on current `main`.

## Managed-file boundary

The role only writes destinations declared by the selected stack. This makes it possible to know which files belong to a deployment and which files must be restored after a failed candidate.

Before changing an already managed stack, the role captures the previous managed files when it can prove the previous boundary from the deployment record and Git history. Candidate-only files are removed during rollback.

If the previous managed set cannot be reconstructed completely, the role does not claim an automatic verified rollback.

## Deployment records

A successful Production run writes a compact record of the accepted state. It currently includes the stack, Git commit, target directory and verification class.

That record is used to locate the previous stack contract during an automatic rollback. Git history remains the source for the exact previous contract and payload.

The record is written after target-side checks pass, not merely after Compose starts.

## Rollback

There are two rollback cases.

### Failed candidate

When a new candidate fails its checks, the role tries to restore the previously accepted managed configuration:

1. read the previous deployment record;
2. load the previous stack contract from Git history;
3. restore the previous managed files;
4. remove files that only existed in the failed candidate;
5. run Compose for the restored configuration;
6. run the previous functional checks again.

The original deployment still exits as failed. The rollback result only tells the operator whether the previous configuration was restored successfully.

### Explicit historical deployment

`scripts/rollback-stack.sh` selects a tagged stack payload and sends it through the same guarded deployment path. It is not a second, weaker maintenance path.

## Configuration versus application data

The rollback mechanism manages configuration files. It does not restore database contents, volumes, uploads, media, indexes or application-generated state.

For a stateless service that distinction is usually straightforward. For a stateful service, a configuration rollback can also be unsafe after a schema or data-format change. The stateful readiness check therefore includes an explicit compatibility decision for rollback to the previously accepted deployment generation.

## Stateful readiness

Stateful stacks can declare an `operations:` section in `stack.yml`. Production then requires a recovery-readiness projection supplied through `HOMELAB_RECOVERY_EVIDENCE` plus the environment's backup-age policy.

The readiness file is checked against a deterministic hash of recovery-relevant parts of the current stack. In practical terms, changes to the image, Compose model, managed configuration, storage declarations or referenced restore runbook require matching readiness evidence for the new generation.

The current check covers:

- the expected stateful service set;
- an isolated restore result;
- functional verification of that restore;
- confirmation that Production was not modified by the restore test;
- whether the applicable RPO/RTO objectives were met;
- configuration-rollback compatibility;
- backup freshness;
- an explicit `ready` result.

The details and JSON format are in [`RECOVERY_READINESS.md`](RECOVERY_READINESS.md).

## Check mode

Production Check Mode uses the same preflight and stack selection as a real deployment. It is intended to show what the guarded path would do, not to provide a bypass around target or stateful checks.

No accepted deployment record is written in check mode.

## CI

CI validates the repository but does not deploy Production.

The main workflow has two useful classes of checks:

1. static checks for Bash, Python, YAML, Ansible syntax, stack contracts, readiness logic and repository rules;
2. a disposable integration test that deploys Dozzle, injects a failure, rolls back and verifies the restored service.

This keeps Production changes operator-driven while still exercising the deployment and rollback code on every relevant change.

## Remote targets

Compose rendering happens on the control machine. Runtime verification happens on the target. Ansible transfers the verifier and contract data needed for the check.

This arrangement avoids depending on repository paths on the target and keeps historical stack selection on the control side. More real remote-host integration coverage is still planned; see [`../ROADMAP.md`](../ROADMAP.md).
