# Deployment records

An accepted deployment writes a durable key/value record and a separate
receipt on the target. Version 2 adds deterministic IDs while preserving the
v1 fields used by interruption recovery and historical rollback.

| Field | Meaning |
| --- | --- |
| `schema_version=2` | Explicit format version; a missing version means legacy v1 |
| `commit`, `tooling_commit` | Exact candidate and control-plane Git commits |
| `contract_hash`, `manifest_hash` | SHA-256 of the candidate `stack.yml` and `MANIFEST.tsv` bytes |
| `stack_contract_id`, `manifest_id` | The same digests with a `sha256:` scheme |
| `target_id` | SHA-256 of the declared `hostname|machine-id` identity string |
| `verification_result_id` | SHA-256 of the verifier's canonical, address-free JSON result |
| `verified`, `verification_result` | Functional check class and PASS disposition |
| `previous_commit`, `previous_record_id` | Frozen rollback lineage |

The record is committed only after target-side functional verification passes.
The receipt binds its transaction ID to the exact record-file SHA-256. A
failed candidate never replaces the last accepted record. Neither the target
ID nor the receipt is a digital signature; local file access is still trusted.

The target also writes `<stack>.result.json` as a side-channel summary of the
latest transaction. It records the terminal result and one of `NOT_NEEDED`,
`NOT_ATTEMPTED`, `UNAVAILABLE`, `FAILED` or `VERIFIED` for rollback, plus the
same Git, contract, manifest and target identities. The writer uses fsync and
atomic rename. If this side-channel write fails, the accepted record and
unresolved marker remain authoritative; the result JSON must not be used to
override them.

Copy the accepted record and receipt to a trusted control host using the
documented read-only target path. To compare them with local Git objects
without fetching or contacting the target:

```bash
python3 scripts/compare-deployment-record.py \
  --record /path/to/dozzle.record \
  --receipt /path/to/dozzle.receipt \
  --repo /path/to/homelab-ops-blueprint \
  --history-ref origin/main --json
```

For a copied terminal result JSON, use `--result-file /path/to/dozzle.result.json`
instead of `--record` and `--receipt`. The command checks the candidate and
tooling commits, Git contract and manifest bytes, outcome consistency, and
target ID shape without contacting the target.

`MATCH` means the candidate and tooling commits exist in the specified local
history, the contract and manifest bytes match their Git objects, the declared
target ID is internally consistent, and the optional receipt matches. An
unavailable Git object or ref is `UNVERIFIABLE`; a contradictory value is
`MISMATCH`. The command is read-only and never fetches from GitHub. It cannot
independently prove that the service was healthy at deployment time; it only
checks the stored verifier result ID's shape and the record's Git and receipt
bindings. Keep the original private runtime evidence for that claim.
