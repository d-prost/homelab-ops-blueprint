# Changelog

Notable project changes are recorded here.

The project follows Semantic Versioning once tagged public releases begin.

## Unreleased

### Added

- guarded Git + Ansible deployment path for Docker Compose stacks;
- target identity and immutable-image checks;
- functional verification and verified configuration rollback;
- durable deployment acceptance records;
- disposable rollback, idempotency and interruption proofs;
- stateful recovery-readiness gate;
- Dozzle and Nginx reference stacks;
- OpenSSF Scorecard and CodeQL workflows;
- public evaluation and remote-SSH proof documentation;
- operational advisory rules for reusable failure-prevention lessons.

### Changed

- historical stack payloads continue to use current validation and deployment logic;
- rollback removes candidate-only managed files and re-verifies the restored stack;
- stateful readiness evidence is tied to the recovery-relevant stack generation;
- backup freshness is supplied by the environment rather than hard-coded;
- documentation and repository templates were simplified ahead of v1.0.0.
