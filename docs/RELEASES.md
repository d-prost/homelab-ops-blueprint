# Release Process

The public project uses Semantic Versioning for published releases.

## Release candidate

- merge only reviewed changes to `main`;
- require green CI;
- review OpenSSF Scorecard findings;
- move relevant items from `Unreleased` in `CHANGELOG.md` into a version section;
- verify `make validate` on a clean clone.

## Tag

Create an annotated tag:

```bash
git tag -a v0.1.0 -m "HomeLab Ops Blueprint v0.1.0"
git push origin v0.1.0
```

Git release tags are for the public project itself. Operational environment release tags created by `scripts/tag-release.sh` serve a different purpose and should not be confused with project versions.
