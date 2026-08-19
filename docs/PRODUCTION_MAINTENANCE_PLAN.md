# Production Maintenance Plan

Status: Initial proposal

## Goal

Add a small, policy-driven maintenance layer for a Docker Compose Production environment without weakening the repository's existing deployment-safety model.

The design should automate routine maintenance while keeping high-risk changes explicit and recoverable. It must preserve Git as the desired-state source, immutable image references, functional verification, and controlled rollback.

## Design principles

- Backups must complete and verify successfully before any Production-changing maintenance starts.
- Daily automation should prioritize security and observability, not blanket upgrades.
- Normal package and application updates should run in a defined maintenance window rather than every night.
- Only one host and one application stack should be changed at a time.
- A host must return to a verified healthy state before application maintenance starts.
- A candidate application release must pass functional verification before the pipeline proceeds.
- Application rollback should restore the previous image/configuration state first.
- Database or application-data restore must never be triggered automatically only because a deployment failed.
- Major OS, runtime, database, and application upgrades remain manual controlled changes.
- `latest` tags are not acceptable Production state; updates must resolve to an allowed version and immutable digest.
- No additional orchestration platform is required. Prefer systemd, existing Ansible, Git, Docker Compose, backup tooling, monitoring, and notifications.

## Maintenance model

### Daily cycle

The daily cycle is intentionally conservative:

1. Run application exports and Production backup.
2. Verify backup freshness and integrity.
3. Run host pre-flight checks.
4. Install eligible security updates.
5. Discover pending host and application updates without applying normal feature updates.
6. Run final host and service health verification.
7. Record the maintenance result and emit one summary notification.

If backup verification fails, Production-changing maintenance is skipped.

### Weekly maintenance window

A weekly maintenance window performs routine non-major updates:

1. Confirm a verified backup exists for the current maintenance run.
2. Update one host at a time.
3. Install eligible normal package updates.
4. Reboot only when required.
5. Verify host health after reboot.
6. Update eligible Docker/runtime components according to policy.
7. Update eligible application stacks sequentially.
8. Run functional checks after each stack deployment.
9. Stop further changes after the first failed deployment.
10. Roll back the failed application deployment to its previous immutable state.
11. Verify the restored version.
12. Run final environment-wide verification and publish one summary report.

## Host update policy

| Change type | Default policy |
| --- | --- |
| Security package update | Automatic daily |
| Normal package update within current OS release | Automatic weekly |
| Kernel patch update | Automatic weekly with controlled reboot |
| Docker/runtime patch or minor update | Guarded weekly |
| Docker/runtime major update | Manual |
| Ubuntu release upgrade | Manual |

Package updates that require unexpected removals, dependency replacement outside policy, or distribution upgrades must be blocked for manual review.

## Host sequencing

Production hosts are maintained sequentially. Parallel reboot or maintenance of multiple infrastructure-critical hosts is not allowed by default.

For each host:

```text
backup gate
  -> pre-flight
  -> package update
  -> reboot if required
  -> host verification
  -> continue to next host
```

Failure of a critical host verification stops the maintenance run before application changes continue.

## Host verification

The minimum host verification contract should include:

- required filesystems and backup mounts are present;
- expected network and DNS functionality works;
- Docker Engine and Compose are functional where required;
- no unexpected critical failed systemd units exist;
- disk capacity remains above defined safety thresholds;
- the monitoring agent is reachable;
- critical infrastructure services respond functionally, not only as running processes.

## Application update policy

Application stacks should declare a maintenance policy instead of inheriting one global rule.

### Automatic candidates

Suitable for low-risk or stateless services after successful backup and host verification.

Typical policy:

- patch releases: automatic;
- minor releases: automatic where operational history supports it;
- major releases: manual.

### Guarded candidates

Suitable for stateful services where deployment rollback is proven and data boundaries are documented.

Required flow:

```text
verified backup
  -> resolve allowed candidate version
  -> resolve immutable digest
  -> deploy candidate
  -> functional verification
  -> success: record deployment
  -> failure: restore previous image/configuration state
  -> verify previous release
```

### Manual candidates

Use manual controlled changes for components where version changes commonly involve schema migrations, irreversible state transitions, or multi-step upgrade procedures.

Examples include:

- database major-version upgrades;
- Ubuntu release upgrades;
- Docker/runtime major upgrades;
- application major upgrades;
- application releases explicitly documented as requiring manual migration steps.

## Version-selection rule

The updater should not ask only whether a newer version exists. It should determine the newest version allowed by Production policy.

Example:

```text
installed: 3.4.2
available: 3.4.3, 3.5.0, 4.0.0
policy result:
  3.4.3 -> eligible
  3.5.0 -> eligible or held depending on stack policy
  4.0.0 -> manual
```

Any selected container release must be committed or rendered as an immutable digest before deployment.

## Failure handling

### Application deployment failure

1. Stop further application updates.
2. Restore the previous managed image/configuration state.
3. Reapply the previous release.
4. Run the previous functional verification contract.
5. Record the run as `DEGRADED` if rollback succeeds.
6. Record the run as `FAILED` and alert immediately if rollback does not restore service.

### Data restore

Application-data or database restore is outside automatic deployment rollback.

A failed deployment alone must not trigger data restore. Data recovery should require an explicit incident decision after confirming that the previous application release cannot safely operate on the current data state.

## Maintenance states

The controller should expose only four top-level states:

- `OK`: maintenance completed and Production is healthy;
- `DEGRADED`: a candidate change failed, rollback succeeded, Production is healthy;
- `FAILED`: a critical verification or rollback failed;
- `SKIPPED`: maintenance was intentionally not performed, for example because backup verification failed.

## Reporting

Normal maintenance should produce one concise summary report containing:

- backup result;
- hosts changed and rebooted;
- security and normal package counts;
- application update results;
- held/manual update candidates;
- rollback activity;
- final health state.

Critical failures should alert immediately. Routine success should not generate per-container notification noise.

## Proposed implementation boundary

Keep the first implementation deliberately small:

- one systemd maintenance timer/service;
- one small Bash or Python controller;
- existing Ansible for guarded remote execution and deployment;
- existing backup/restore tooling as the backup gate;
- existing Checkmk monitoring for health state;
- existing ntfy channel for summaries and critical alerts;
- Git as desired state and deployment history.

Do not add AWX, Rundeck, Jenkins, Kubernetes, Argo CD, or another orchestration platform unless a concrete operational limitation later justifies it.

## Initial implementation phases

### Phase 1: Observe only

- inventory Production hosts and update domains;
- discover pending APT and application updates;
- classify updates according to policy;
- generate a report without changing Production.

### Phase 2: Host security maintenance

- add the verified-backup gate;
- enable daily security-package maintenance;
- add reboot-required detection;
- verify host health before and after maintenance.

### Phase 3: Weekly host maintenance

- enable eligible normal package updates;
- sequence hosts serially;
- implement controlled reboot and stop-on-failure behavior.

### Phase 4: Application maintenance

- add per-stack maintenance policy metadata;
- resolve allowed versions to immutable image digests;
- update one stack at a time;
- reuse existing functional verification and transactional configuration rollback.

### Phase 5: Operational hardening

- expose maintenance state to monitoring;
- add concise ntfy reports;
- retain machine-readable maintenance receipts;
- test failed-update and rollback scenarios in a disposable or experimental environment before enabling them in Production.

## Non-goals

This proposal does not introduce:

- automatic Production deployment from public CI;
- automatic database or application-data rollback;
- unattended OS release upgrades;
- blanket `latest`-tag updates;
- parallel Production host maintenance;
- a new orchestration platform.

## Open design questions

Before implementation, define:

1. the exact Production host dependency order;
2. which package classes are eligible for unattended normal updates;
3. the initial per-stack application policy (`auto`, `guarded`, `manual`);
4. which functional checks are required for each critical service;
5. the exact backup receipt that authorizes a maintenance run;
6. the maintenance window and reboot policy;
7. how candidate image versions and digests are written back into desired state without bypassing review expectations.
