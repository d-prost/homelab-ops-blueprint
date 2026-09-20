# Remote SSH proof evidence

> Copy this template only after a real remote proof run. Replace placeholders
> with public-safe facts. Do not include private hostnames, addresses, users,
> SSH material, deployment records, backup identifiers or recovery evidence.

- Date: `YYYY-MM-DD`
- Repository commit: `<40-char commit>`
- Topology: `separate SSH target`
- Target OS: `<distribution + version>`
- Docker Engine: `<version>`
- Docker Compose: `<version>`
- Ansible Core: `<version>`

## Baseline deployment

- SSH host-key verification: `PASS`
- Declared hostname verification: `PASS`
- Optional machine-ID verification: `NOT CONFIGURED | PASS`
- Candidate deployment: `PASS`
- Functional verification: `PASS`
- Durable acceptance: `PASS`
- Elapsed time: `<non-sensitive duration>`

## Injected failure

- Failure fixture: `disposable Dozzle candidate exits immediately`
- Candidate result: `REJECTED`
- Rollback entered: `YES`
- Previous managed files restored: `PASS`
- Previous Compose model reapplied: `PASS`
- Previous functional verification: `PASS`
- Terminal result: `REJECTED_ROLLBACK_VERIFIED`
- Elapsed time: `<non-sensitive duration>`

## Cleanup

- Disposable stack removed: `PASS`
- Project-managed target files removed: `PASS`
- Private inventory committed: `NO`
- Private SSH material committed: `NO`

## Notes

Record only reproducible, public-safe compatibility observations here.
