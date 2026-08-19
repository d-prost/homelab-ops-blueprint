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

## Convergence lifecycle

```text
reviewed Git desired state
      |
      +--> clean tree / main / origin equality guard
      +--> selected stack payload
      +--> current private inventory
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

Stateful adoption therefore requires a separate proof boundary: application-aware export or backup, isolated restore, and functional restore verification. The stateful adoption checklist documents this requirement. Future work may turn that checklist into a machine-enforced readiness gate, but must not imply that configuration rollback is equivalent to data recovery.

## Design constraints

The project favors explicit proof over automatic reconciliation and bounded mechanisms over broad platforms.

Deliberate exclusions include:

- no general cluster orchestration;
- no Kubernetes requirement;
- no always-on GitOps controller requirement;
- no automatic Production deployment from public CI;
- no stateful database migration automation;
- no backup writer in the public blueprint;
- no secret-store implementation in the public blueprint;
- no firewall management framework;
- no private infrastructure inventory;
- no feature expansion that weakens target identity, immutable images, bounded mutation, verification, or rollback proof.

Environment-specific private operations may implement secrets, backups, monitoring, scheduling, and offsite recovery around this core model.
