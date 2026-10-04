# Roadmap

The roadmap is intentionally small and is not tied to fixed release dates.

## v1.0.0

The first stable release is defined by the transaction contract in [`docs/TRANSACTION_MODEL.md`](docs/TRANSACTION_MODEL.md), not by feature count.

Already implemented:

- stack-contract and functional-check validation;
- two stateless reference stacks;
- disposable rollback and idempotency proofs;
- interruption and acceptance-persistence handling;
- frozen candidate and tooling identities;
- SSH transport and target identity checks;
- rollback-material and immutable-image preflight;
- host-global serialization;
- durable acceptance semantics.

Remaining release gates:

- #37 — effective GitHub `main` change controls;
- #35 — a real separate-target SSH transaction and rollback proof;
- one final clean-checkout proof pass before tagging `v1.0.0`.

The final sequence is documented in [`docs/V1_FINAL_ACCEPTANCE.md`](docs/V1_FINAL_ACCEPTANCE.md).

## Stateful reference stack

Issue #9 tracks the first complete public stateful recovery example:

- explicit data and secret boundaries;
- application-aware export;
- isolated restore;
- representative data verification;
- schema-sensitive rollback compatibility;
- measured recovery evidence.

This remains separate from the first stateless v1 release.

## Deployment records

Possible follow-up work:

- versioned record format;
- stable contract and target identifiers;
- clearer candidate-failure and rollback results;
- optional JSON output;
- offline comparison against Git history.

## Multi-host support

Multi-host work stays behind the single-host transaction boundary. Likely additions include:

- explicit stack-to-host selection;
- inventory groups;
- serial and canary rollout;
- per-host results;
- defined partial-failure semantics.

## Operational lessons

The advisory registry remains read-only and non-authoritative. Any later tooling should explain relevant rules without gaining deployment or approval authority.

## Later ideas

Only if there is a concrete need:

- deterministic hashes for additional artifacts;
- optional record signing;
- independent Git-history verification;
- reusable validation helpers;
- drift reporting without automatic reconciliation.
