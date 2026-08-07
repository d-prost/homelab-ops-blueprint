# Contributing

Thank you for helping improve HomeLab Ops Blueprint.

The project values small, reviewable changes that improve safety and reproducibility without turning a small-environment blueprint into an orchestration platform.

## Before opening a pull request

1. Fork the repository and create a focused branch.
2. Keep all examples environment-neutral.
3. Never include real infrastructure identifiers, credentials, backup evidence, private keys, or secret environment files.
4. Run:

   ```bash
   make validate
   ```

5. If you changed deployment or rollback behavior, also run the disposable Lab proof on a clean Linux host:

   ```bash
   make lab-proof
   ```

6. Add or update a focused test for safety-sensitive behavior.
7. Update documentation when operator behavior changes.

## Pull request expectations

A good pull request:

- explains the operational problem;
- keeps the scope small;
- describes the safety boundary;
- includes validation evidence;
- avoids unrelated formatting churn;
- does not make Production deployment automatic;
- does not weaken immutable-image or host-identity requirements.

## Good first contributions

Useful first contributions include:

- clearer documentation or examples;
- additional contract-validation tests;
- portable error handling;
- functional health-check improvements;
- new stateless example stacks with pinned image digests;
- public-safety checks with low false-positive rates.

## Review policy

Maintainers may request changes when a contribution is convenient but weakens rollback, validation, or the public/private boundary. Safety properties take precedence over reducing a few lines of configuration.
