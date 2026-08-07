# Functional Restore Drill Template

Use one copy per real restore exercise in a private evidence location. Do not commit real backup identifiers or restored personal data to a public repository.

## Metadata

| Field | Value |
|---|---|
| Service | |
| Date | |
| Operator | |
| Isolated Lab host | |
| Backup source | Local / Offsite / Offline |
| Backup reference | PRIVATE |
| Image digest | |
| Database major version | |

## Targets and measurements

| Metric | Target | Measured | Result |
|---|---:|---:|---|
| RPO | | | PASS / FAIL |
| RTO to first usable function | | | PASS / FAIL |

## Isolation precheck

- [ ] Production databases and storage are unreachable from the Lab.
- [ ] Outbound notifications are disabled.
- [ ] Lab DNS names cannot conflict with Production.
- [ ] Cleanup is defined before restore starts.

## Restore procedure

1.
2.
3.

## Functional acceptance

- [ ] application starts;
- [ ] authentication works where applicable;
- [ ] representative user function works;
- [ ] representative restored object/hash matches where applicable.

## Result

Result: `PASS` / `FAIL` / `PARTIAL`

Document gaps without copying secrets or private topology into public Git.
