# Functional restore drill template

Keep one private copy per real restore exercise. Backup identifiers and restored personal data do not belong in the public repository.

## Metadata

| Field | Value |
|---|---|
| Service | |
| Date | |
| Evidence owner | |
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
- [ ] representative function works;
- [ ] representative restored object or hash matches where applicable.

## Result

Result: `PASS` / `FAIL` / `PARTIAL`

Document gaps without copying secrets or private topology into public Git.
