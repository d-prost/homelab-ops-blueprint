# Roadmap

The roadmap favors reusable operational value over feature count.

## Near term

- add deeper unit tests for functional-check contract parsing;
- document one additional stateless stack example;
- publish a first stable release after CI and Scorecard are consistently green;
- collect real user feedback before expanding the abstraction layer.

## Later, when justified by users

- reusable stack-contract examples for additional Compose services;
- optional JSON output for validation tools;
- a small reusable validation action or package if external repositories need it;
- executable remote-target integration proof when a safe disposable target is available.

## Completed from operational feedback

- separate current control-plane code from historical release payloads;
- support remote targets without repository checkouts;
- verify rollbacks with the exact prior Git contract;
- validate source-to-target manifests;
- document stateful adoption and restore boundaries.

## Explicitly not a goal

- general cluster orchestration;
- automatic Production deployment from public CI;
- storing Production inventory or secrets in the repository;
- automatic rollback of databases or application data;
- adding governance machinery without an actual community need.
