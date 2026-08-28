# Architecture

## Architectural thesis

HomeLab Ops Blueprint implements **Verified Convergence** for small Docker Compose environments.

The goal is not merely to make a target look like Git. The goal is to accept a new Production state only when the system can establish a bounded chain of evidence from reviewed desired state to verified runtime, while preserving a deterministic and verifiable path back to the exact previously accepted contract.

Verified Convergence is built from seven properties:

1. **Authorized desired state** — the candidate originates from reviewed Git under explicit branch and remote-equality guards.
2. **Exact target identity** — the selected inventory and the actual target hostname must agree exactly.
3. **Contract-bounded mutation** — only files declared by the stack contract and matching manifest may be installed.
4. **Immutable runtime inputs** — managed container images must be pinned by digest.
5. **Functional runtime proof** — success requires expected services and functional checks, not just container creation.
6. **Recorded acceptance evidence** — the accepted Git commit and target are persisted as a deployment receipt.
7. **Verified rollback** — a failed candidate may roll back only when the exact prior Git contract and complete prior managed file set are available, and the restored runtime passes the prior functional contract again.

These properties are intentionally stronger than a generic `docker compose up` workflow and intentionally smaller in scope than cluster orchestration.

## Trust boundaries

- **Reviewed Git desired state:** source of the candidate stack contract and payload.
- **Current control plane:** current `main` inventory, identity guards, playbooks, roles, validation logic, and verifier.
- **Release payload:** only the selected `stacks/<name>/` directory from `HEAD` or an annotated operational release.
- **Target runtime:** Docker, Compose, Python, managed files, persistent application data, secrets, and deployment receipts.
- **Git history:** authoritative source for the exact previously accepted stack contract during rollback.
- **Private operations boundary:** real topology, credentials, backup evidence, private PKI, and recovery material remain outside the public repository.

Historical releases never supply executable automation. Old payloads may describe an old stack, but they cannot replace current safety logic, current inventory, or current verification code.

## Authority model

CI validates repository consistency; it does not have Production deployment authority. Human review decides what enters `main`, and an operator performs a separate explicit Production convergence action.

```text
operator -> Git / pull request -> CI validation -> human review / merge -> clean main
operator -----------------------------------------------------> explicit converge
clean main ---------------------------------------------------> guarded converge
                                                               |
                                                               v
target runtime -> functional verification -> acceptance evidence
```

This separation is deliberate. A green CI run is evidence that the repository satisfies its static and disposable proof suite; it is not permission for CI to mutate Production.

## Convergence lifecycle

```text
reviewed Git desired state
      |
      +--> clean tree / main / origin equality guard
      +--> selected stack payload
      +--> current private inventory
      +--> acquire the single non-blocking deployment lock
      |
      v
control-plane preflight
      |
      +--> require explicit release metadata
      +--> verify exact target identity
      +--> render candidate Compose model
      +--> require immutable image digests
      +--> validate stack.yml against MANIFEST.tsv
      |
      v
bounded candidate transaction
      |
      +--> stage only declared managed files
      +--> capture exact prior managed files when rollback is provable
      +--> install only allowlisted destinations
      +--> docker compose up -d
      |
      v
runtime proof
      |
      +--> expected-service set
      +--> transferred functional verifier
      +--> staged contract on the real target
      |
      +--> success: write deployment receipt
      |
      +--> failure: enter verified rollback path
```

## Production mutation invariants

Production-changing operations should remain deliberately boring:

- **One guarded mutation path.** Normal deployment and explicit rollback reuse `scripts/deploy-stack.sh`; wrappers may select a payload, but they must not create a weaker maintenance or rollback path around the Production guards.
- **Serialized convergence.** The operator entry point uses one non-blocking `flock` lock and refuses a second concurrent deployment. Parallel mutation of the same environment is treated as an error, not as throughput to optimize.
- **No routine-change bypass.** Image-only updates, routine maintenance, redeployments, and rollbacks are still Production mutations and must preserve the same authorization, target, verification, and recovery boundaries.
- **Current safety logic wins.** Historical payloads may supply stack files only. They never supply historical inventories, roles, helper scripts, or safety logic.
- **Acceptance follows runtime proof.** A deployment record is written only after target-side verification succeeds; check mode and CI validation do not create Production acceptance evidence.

These rules keep convenience features from becoming parallel control planes.

## Verified rollback lifecycle

Rollback is not defined as "run an older Compose file." It is a second convergence operation whose target is the previously accepted contract.

```text
candidate failure
      |
      v
prior deployment receipt
      |
      +--> require exactly one prior Git commit
      |
      v
exact prior contract from Git history
      |
      +--> validate rollback boundary compatibility
      +--> require complete prior managed-file set
      |
      v
restore transaction
      |
      +--> restore prior allowlisted files
      +--> remove candidate-only files
      +--> reapply prior Compose model
      |
      v
prior runtime proof
      |
      +--> expected prior services
      +--> exact prior functional contract
      |
      +--> verified: report candidate failure with successful rollback
      +--> unverifiable: fail closed
```

A rollback is therefore successful only when the previous state is both restored and functionally re-proven.

## Evidence model

Today the implementation records a compact deployment receipt containing the stack, accepted Git commit, target directory, and verification class. The long-term evidence model is intentionally machine-readable and should allow an independent verifier to answer:

- Which Git commit authorized this state?
- Which stack contract defined the mutation boundary?
- Which target accepted it?
- Which image digests were permitted?
- Which declared files were installed?
- Which functional checks passed?
- Which previous accepted state is available for rollback?
- Was rollback itself re-verified when used?

Future evidence work must extend the existing safety model rather than create a parallel deployment path.

## Remote-target model

Compose rendering remains on the control plane. Runtime checks and functional verification execute on the target, with the verifier and contract transferred by Ansible. The target therefore needs Docker, Compose and Python, but no repository checkout.

This split is deliberate: a local Ansible connection can conceal path and trust-boundary mistakes. At least one bounded real remote deployment is required before claiming the remote-target property is proven end to end.

## Stateful boundary

Verified Convergence currently protects declared configuration convergence. It does **not** claim transactional rollback of databases, media, indexes, uploads, named volumes, application-generated state, or secrets.

The optional `operations:` contract validates **operational coverage declarations** such as persistent mounts, backup policy identity, restore runbook, restore-verification intent, and monitoring intent. Those declarations are not evidence that the service is currently recoverable.

A future Production readiness gate for a stateful stack must keep four questions separate:

1. Is the state boundary declared completely?
2. Has an isolated functional restore actually passed?
3. Is the applicable backup evidence current enough for the environment's real backup cadence?
4. Is the stack explicitly recovery-ready for this mutation?

Snapshot existence, a green timer, or a declared restore runbook answers none of those questions by itself. Backup freshness must be derived from the real backup cadence plus a bounded operational margin; the public blueprint should not encode one universal age such as 12 or 30 hours.

Routine image updates and other apparently small stateful mutations must not bypass the same readiness gate. Private backup receipts and restore evidence remain private; the public project should define the contract and validation boundary, not become the backup writer.

## Ongoing monitoring boundary

Target-side functional checks are **deployment acceptance checks**, not a replacement for ongoing monitoring. A private environment may use Checkmk, Prometheus, another monitoring system, or simple local checks as its runtime-health authority. The blueprint should consume only the minimum monitoring intent needed by a stack contract and should not create a second alerting or operational-truth path.

## Design constraints

The project favors explicit proof over automatic reconciliation and bounded mechanisms over broad platforms.

Deliberate exclusions include:

- no general cluster orchestration;
- no Kubernetes requirement;
- no always-on GitOps controller requirement;
- no automatic Production deployment from public CI;
- no parallel Production mutation path for routine maintenance;
- no stateful database migration automation;
- no backup writer in the public blueprint;
- no monitoring platform in the public blueprint;
- no secret-store implementation in the public blueprint;
- no firewall management framework;
- no private infrastructure inventory;
- no feature expansion that weakens target identity, immutable images, bounded mutation, verification, or rollback proof.

Environment-specific private operations may implement secrets, backups, monitoring, scheduling, and offsite recovery around this core model.
