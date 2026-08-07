#!/usr/bin/env bash
set -Eeuo pipefail
((EUID != 0)) || { printf 'ERROR: run as normal operator.\n' >&2; exit 1; }
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"; cd "$repo_root"
[[ "$(git branch --show-current)" == "main" ]] || exit 1
[[ -z "$(git status --porcelain --untracked-files=all)" ]] || exit 1
git fetch --quiet origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || exit 1
tag="release-$(date -u +%Y%m%d-%H%M%SZ)"
git tag -a "$tag" -m "Verified Production release"; git push origin "$tag"; printf 'Created release tag: %s\n' "$tag"
