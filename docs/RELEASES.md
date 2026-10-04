# Release Process

The public project uses Semantic Versioning for published releases.

## Release candidate

For the first stable release, complete the operator handoff in
[`V1_FINAL_ACCEPTANCE.md`](V1_FINAL_ACCEPTANCE.md) first.

Then:

- merge only reviewed changes to `main`;
- require green CI;
- review OpenSSF Scorecard findings;
- move relevant items from `Unreleased` in `CHANGELOG.md` into the
  `v1.0.0` section;
- keep issue #9 and later advisory tooling outside the v1 release boundary;
- tag only after the final acceptance run is complete.

## Tag

Create an annotated tag:

```bash
git tag -a v1.0.0 -m "HomeLab Ops Blueprint v1.0.0"
git push origin v1.0.0
```

Git release tags are for the public project itself. Operational environment release tags created by `scripts/tag-release.sh` serve a different purpose and should not be confused with project versions.
