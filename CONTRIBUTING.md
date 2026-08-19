# Contributing

Thank you for helping improve HomeLab Ops Blueprint.

The project values small, reviewable changes that strengthen **Verified Convergence** without turning a small-environment blueprint into a general orchestration platform.

A useful contribution should improve at least one of these properties:

- authorized desired state;
- exact target identity;
- contract-bounded mutation;
- immutable runtime inputs;
- functional runtime proof;
- machine-readable acceptance evidence;
- verified rollback;
- recovery readiness for stateful services.

## Before opening a pull request

1. Fork the repository and create a focused branch.
2. Keep all examples environment-neutral.
3. Never include real infrastructure identifiers, credentials, backup evidence, private keys, or secret environment files.
4. Run:

   ```bash
   make validate
   ```

5. If you changed deployment, verification, evidence, or rollback behavior, also run the disposable Lab proof on a clean Linux host:

   ```bash
   make lab-proof
   ```

6. Add or update a focused test for safety-sensitive behavior.
7. Update documentation when an operator-visible contract or proof property changes.

## Pull request expectations

A good pull request:

- explains the operational problem;
- states which Verified Convergence property it strengthens;
- keeps the scope small;
- describes the safety boundary;
- includes validation evidence;
- avoids unrelated formatting churn;
- does not make Production deployment automatic by default;
- does not weaken immutable-image, host-identity, mutation-boundary, functional-verification, or rollback requirements.

A change that adds a large dependency, controller, daemon, or abstraction should explain why the same proof property cannot be preserved with a smaller mechanism.

## Good first contributions

Useful first contributions include:

- clearer documentation or examples;
- additional contract-validation tests;
- failure-path tests;
- portable error handling;
- functional verification improvements;
- richer machine-readable evidence;
- an additional stateless example stack with pinned image digests;
- public-safety checks with low false-positive rates.

## Review policy

Maintainers may request changes when a contribution is convenient but weakens the Verified Convergence chain or the public/private boundary. Safety and independent verifiability take precedence over reducing a few lines of configuration or adding feature breadth.
