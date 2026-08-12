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
- OpenSSF Scorecard workflow and community health files.
- source-to-target `MANIFEST.tsv` validation;
- remote-target functional verification without target-side Git checkouts;
- stateful-service adoption and recovery checklist.

### Changed

- keep current inventory, Ansible logic, and verification code authoritative when deploying historical stack payloads;
- derive rollback eligibility from a prior deployment receipt and verify the restored release with its exact Git contract;
- support nested managed-file paths and remove candidate-only files during rollback.
