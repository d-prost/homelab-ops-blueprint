# Maintainer Checklist

Some important open-source settings live in GitHub rather than in repository files.

## Repository settings

After publishing:

- set the repository description and relevant topics;
- enable Issues and Discussions if you intend to support community participation;
- enable automatically deleting head branches after merge;
- enable Dependabot alerts and security updates;
- enable Private Vulnerability Reporting;
- configure Repository Rules for `main` requiring pull requests and the `Static validation` and `Disposable rollback proof` checks;
- keep default `GITHUB_TOKEN` workflow permissions read-only unless a specific workflow requires more;
- do not add repository secrets unless a real feature needs them.

## OpenSSF

The repository includes a Scorecard workflow. Review findings after the first public run and improve real weaknesses rather than optimizing a number for its own sake.

## Releases

Before the first stable release:

1. keep CI green on `main`;
2. review Scorecard findings;
3. update `CHANGELOG.md`;
4. ensure examples contain no private infrastructure data;
5. create an annotated semantic-version tag;
6. create GitHub release notes from the reviewed changelog.

## Community health

Respond to valid issues, label approachable work, review external pull requests promptly, and keep contribution documentation current. External contributors should be real collaborators solving real problems, not manufactured accounts or trivial metric-padding.
