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

## Read-only configuration drift report

Copy the accepted record and the complete managed stack directory into a
private snapshot root that preserves absolute target paths. For example,
`/private/snapshot/opt/homelab-ops/stacks/dozzle/` should contain the copied
managed files. Then run:

```bash
python3 scripts/report-config-drift.py \
  --record /private/dozzle.record \
  --receipt /private/dozzle.receipt \
  --snapshot-root /private/snapshot \
  --repo /path/to/homelab-ops-blueprint \
  --history-ref origin/main --json
```

The report first checks the accepted record against local Git history. It then
compares each manifest-managed target file byte for byte, publishing stable
SHA-256 values and `MATCH`, `DIFFERENT`, `MISSING`, or `UNSAFE`. It reads only
the copied snapshot and local Git objects. The snapshot, receipt and output
remain private. Extra files outside the accepted manifest and the current
Docker process state are not classified; `current_runtime` is always
`NOT_CHECKED`. A historical acceptance record is not a current health claim.

## Optional operator signature

An operator can sign an exact copy of the accepted record after deployment.
Keep the signing key, signature and allowed-signers file outside the public
repository. The key remains on the trusted control host and never reaches the
target:

```bash
python3 scripts/sign-deployment-record.py sign \
  --record /private/dozzle.record \
  --key /private/operator-ed25519 \
  --output /private/dozzle.record.sig

python3 scripts/sign-deployment-record.py verify \
  --record /private/dozzle.record \
  --signature /private/dozzle.record.sig \
  --allowed-signers /private/allowed_signers \
  --identity operator
```

The allowed-signers file uses the OpenSSH format, for example
`operator ssh-ed25519 AAAA...`. Verification binds the signer identity and exact
record bytes to the fixed `homelab-ops-blueprint-record` namespace. A changed
record or untrusted signer fails. Signatures are optional evidence; they do not
change the target's acceptance commit point, verify current runtime health, or
replace the receipt and Git-history comparison.
