# Roadmap

The roadmap favors reusable operational value over feature count.

## Near term

- harden validation and failure messages;
- add unit tests for functional-check contract parsing;
- document one additional stateless stack example;
- publish a first stable release after CI and Scorecard are consistently green;
- collect real user feedback before expanding the abstraction layer.

## Later, when justified by users

- reusable stack-contract examples for additional Compose services;
- optional JSON output for validation tools;
- a small reusable validation action or package if external repositories need it;
- migration guidance for stateful services without pretending configuration rollback is data recovery.

## Explicitly not a goal

- Kubernetes, Swarm, or general cluster orchestration;
- automatic Production deployment from public CI;
- storing Production inventory or secrets in the repository;
- automatic rollback of databases or application data;
- adding governance machinery without an actual community need.
