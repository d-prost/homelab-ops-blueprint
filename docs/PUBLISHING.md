# Publishing Safely

Create this public project as a new repository with a fresh history. Do not copy `.git` from a private operational repository.

## Local initialization

```bash
cd homelab-ops-blueprint
git init -b main
git add .
git status --short
git commit -m "Initial public HomeLab operations blueprint"
```

Before the first push, run a secret scan with Gitleaks if available:

```bash
gitleaks git . --redact --no-banner --config .gitleaks.toml
```

## GitHub repository

Create a new empty repository, for example `homelab-ops-blueprint`, and make that new repository Public. Do not change the visibility of the private operational repository.

Then add the new remote and push:

```bash
git remote add origin git@github.com:YOUR_ACCOUNT/homelab-ops-blueprint.git
git push -u origin main
```

## Before every public push

Check that no real environment data slipped in:

```bash
git diff --cached --check
git grep -nE 'CHANGE_ME|password|token|secret|private_key' -- ':!docs/PUBLIC_PRIVATE_BOUNDARY.md'
```

The grep is only a review aid, not a substitute for Gitleaks or human review.
