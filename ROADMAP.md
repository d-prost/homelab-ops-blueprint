# Roadmap

This is the working list of what I want to improve next. I do not tie it to fixed release dates.

## First stable release

I define `v1.0.0` by the transaction contract in [`docs/TRANSACTION_MODEL.md`](docs/TRANSACTION_MODEL.md). My goal is to prove that contract, not to add platform breadth.

The baseline already includes:

- focused unit coverage around stack-contract and functional-check parsing;
- two stateless reference stacks;
- a clean evaluation path from a fresh checkout;
- disposable rollback, idempotency, interruption and acceptance-persistence proofs;
- frozen candidate and tooling identities;
- SSH transport and target identity checks;
- rollback-material and immutable-image preflight;
- host-global serialization on one configured control host;
- durable acceptance semantics.

## Final v1 acceptance

I keep the remaining v1 work in one final acceptance pass rather than expanding the framework again.

[`docs/V1_FINAL_ACCEPTANCE.md`](docs/V1_FINAL_ACCEPTANCE.md) is my authoritative handoff for that pass.

The two remaining external gates are:

- #37 — effective GitHub `main` change controls and blocked-merge proof;
- #35 — a real separate-target SSH transaction and rollback proof.

After those gates, I run the complete local proof set once from clean `main` and tag `v1.0.0` only if the final pass is green.

Additional parser coverage, failure cases and external reports remain useful, but I do not treat them as reasons to expand the v1 boundary unless the final acceptance run exposes a concrete defect.

## External validation

I keep the repository independently evaluable without private HomeLab access. [`docs/EVALUATION.md`](docs/EVALUATION.md) is the public evaluation path.

Useful evidence includes clean-host validation, disposable deployment results, separate-target reports and reproducible bug reports. I keep private hostnames, addresses, credentials, backup identifiers, deployment receipts and recovery evidence out of public Git history.

## Deployment records

I want to improve accepted deployment records without turning them into another control plane.

Planned improvements include:

- a versioned record format;
- stable identifiers for the contract, manifest, target and verification result;
- clearer candidate-failure and rollback outcomes;
- JSON output where machine consumption is useful;
- an offline comparison between copied records and Git history.

## Stateful services

The first readiness gate exists. My next stateful work is a fully synthetic, public-safe reference proof that covers:

- explicit data, secret, export and restore boundaries;
- application-aware export;
- isolated restore;
- representative content verification;
- schema-sensitive rollback compatibility;
- measured recovery evidence.

Configuration rollback and application-data recovery remain separate mechanisms.

## Multi-host support

I keep multi-host work behind the single-host proof boundary.

The next design layer may include:

- explicit stack-to-host selection;
- reusable inventory groups;
- serial and canary rollout;
- one result per host;
- defined partial-failure semantics.

## Advisory tooling

I keep the Production-derived advisory registry read-only and non-authoritative.

A later advisor may explain which public-safe rules apply to a proposed change. It will not deploy, approve, mutate Production or silently turn advice into policy.

## Later ideas

I will only add these when a concrete need justifies them:

- deterministic hashes for more deployment artifacts;
- optional signing of deployment records;
- independent verification against Git history;
- reusable validation tooling for other repositories;
- drift reporting without automatic reconciliation.
