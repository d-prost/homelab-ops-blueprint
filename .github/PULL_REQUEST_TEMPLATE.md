## Problem

What operational problem does this change solve?

## Change

Describe the smallest relevant change.

## Safety boundary

- [ ] No real infrastructure identifiers or secrets are included.
- [ ] Production remains manual.
- [ ] Host-identity and immutable-image guards are preserved.
- [ ] Rollback/data-recovery boundaries remain explicit.

## Validation

- [ ] `make validate`
- [ ] `make lab-proof` when deployment/rollback behavior changed
- [ ] Documentation updated when operator behavior changed
