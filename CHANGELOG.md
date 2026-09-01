# Changelog

All notable project changes are recorded here.

The project follows Semantic Versioning once tagged public releases begin.

## Unreleased

### Added

- public-safe Git/Ansible Docker Compose operations blueprint;
- transactional configuration rollback;
- functional HTTP verification;
- disposable CI rollback proof;
- public-safety validation and complete-history secret scanning;
- OpenSSF Scorecard workflow and community health files;
- source-to-target `MANIFEST.tsv` validation;
- remote-target functional verification without target-side Git checkouts;
- stateful-service adoption and recovery checklist;
- machine-checkable stateful recovery-readiness gate consuming private evidence outside public Git;
- exact public-stack-generation hashing for recovery-evidence applicability;
- recovery-readiness regression coverage for stale evidence, failed restore, service-scope mismatch, unsafe evidence files, generation changes, and historical-classification bypasses.

### Changed

- keep current inventory, Ansible logic, verification code, and recovery-readiness logic authoritative when deploying historical stack payloads;
- derive rollback eligibility from a prior deployment receipt and verify the restored release with its exact Git contract;
- support nested managed-file paths and remove candidate-only files during rollback;
- require environment-supplied backup-freshness policy instead of embedding one public cadence;
- invalidate stateful readiness evidence after recovery-relevant public runtime changes while leaving monitoring-only intent outside the proof hash.
