# Governance

HomeLab Ops Blueprint is maintained as a small open-source project with transparent technical decision making.

## Roles

### Maintainers

Maintainers review contributions, manage releases, security reports, repository settings, and the project roadmap.

### Contributors

Anyone who submits documentation, tests, code, reviews, or reproducible issue reports is a contributor.

## Decision model

Routine changes are accepted through pull-request review. Changes that alter the safety model should document:

- the problem being solved;
- the threat or failure mode considered;
- the new invariant or guard;
- rollback implications;
- validation evidence.

The project prefers backwards-compatible, incremental changes. Breaking changes require a documented migration path and a major release.

## Maintainer growth

Sustained contributors may be invited to help triage issues and review pull requests before receiving broader maintainer responsibilities. Access should follow demonstrated contribution and least privilege.

## Conflict of interest

Reviewers should disclose material conflicts when reviewing a contribution tied to their own commercial product or service.
