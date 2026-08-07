# Contributing

Keep contributions environment-neutral and safe for a public repository.

Before submitting a pull request:

1. run `scripts/validate-repository.sh`;
2. do not include real infrastructure identifiers or secrets;
3. keep Production deployment manual;
4. preserve immutable image references for managed stacks;
5. add or update a functional check for changed runtime behavior;
6. add a focused test when changing deployment guards or rollback logic.

A change that makes the example easier to copy but weakens the safety boundary should be rejected.
