# Release process

Published project releases use Semantic Versioning.

Operational environment tags created by `scripts/tag-release.sh` are separate from public project versions.

## v1.0.0

The first stable release follows [`V1_FINAL_ACCEPTANCE.md`](V1_FINAL_ACCEPTANCE.md).

Release criteria:

- final v1 acceptance complete;
- relevant CI green;
- OpenSSF Scorecard reviewed;
- release notes aligned with implemented support;
- post-v1 work kept outside the release claim.

Relevant `Unreleased` entries in `CHANGELOG.md` move into `v1.0.0` only after final acceptance.

## Tag

```bash
git tag -a v1.0.0 -m "HomeLab Ops Blueprint v1.0.0"
git push origin v1.0.0
```

Project-version tags and operational environment tags serve different purposes and remain separate.
