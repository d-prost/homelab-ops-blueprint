# Release process

I use Semantic Versioning for published project releases.

Operational environment tags created by `scripts/tag-release.sh` are separate from public project versions.

## First stable release

I only prepare `v1.0.0` after completing [`V1_FINAL_ACCEPTANCE.md`](V1_FINAL_ACCEPTANCE.md).

My release boundary is:

- final v1 acceptance complete;
- relevant CI green;
- OpenSSF Scorecard reviewed;
- release notes aligned with the actual supported boundary;
- post-v1 work kept outside the release claim.

I move the relevant `Unreleased` entries in `CHANGELOG.md` into the `v1.0.0` section only after the acceptance pass is complete.

## Tag

My project release tag is:

```bash
git tag -a v1.0.0 -m "HomeLab Ops Blueprint v1.0.0"
git push origin v1.0.0
```

I keep project-version tags and operational environment tags conceptually separate.
