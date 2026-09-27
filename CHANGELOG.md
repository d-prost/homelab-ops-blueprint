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
- recovery-readiness regression coverage for stale evidence, failed restore, service-scope mismatch, unsafe evidence files, generation changes, and historical-classification bypasses;
- Nginx as a second stateless reference stack using the same deployment contract as the Dozzle example;
- a reproducible evaluation guide for reviewers and prospective adopters;
- a synthetic Redis reference stack with pinned image, disposable RDB export,
  isolated restore, representative content verification, and measured recovery timings;
- a Redis PING functional check and required CI recovery proof;
- a public-safe report of a real separate-target SSH deployment and verified rollback.

### Changed

- keep current inventory, Ansible logic, verification code, and recovery-readiness logic authoritative when deploying historical stack payloads;
- derive rollback eligibility from a prior deployment receipt and verify the restored release with its exact Git contract;
- support nested managed-file paths and remove candidate-only files during rollback;
- require environment-supplied backup-freshness policy instead of embedding one public cadence;
- invalidate stateful readiness evidence after recovery-relevant public runtime changes while leaving monitoring-only intent outside the proof hash;
- improve first-time onboarding with a complete clone/setup path, explicit project scope, maturity boundaries and external evaluation guidance;
- define evidence-based criteria for the first stable release instead of treating repository age or popularity as release gates.
- report remote proof facts without exposing inventory names or misinterpreting Docker's Go template as Ansible/Jinja syntax.
- version accepted deployment records and add deterministic identity fields,
  structured verifier results, and an offline Git/receipt comparison command.
