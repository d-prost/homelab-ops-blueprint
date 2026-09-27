# Synthetic Redis recovery proof, 2026-09-27

This public-safe report describes one disposable Linux Docker host evaluation
of `tests/test-stateful-redis-recovery.sh`. It contains no target identity,
network address, credential, private backup reference or Production data.

## Result

| Check | Observation |
| --- | --- |
| Required backup input absent | Refused before `SAVE` and before any export file existed |
| Source record | Deterministic synthetic key written through `redis-cli` |
| Export | Redis `SAVE` produced a non-empty RDB with SHA-256 recorded by the proof |
| Source destruction | Original Compose project and named data volume removed |
| Isolated restore | RDB imported into a newly created volume and Compose project |
| Runtime check | Redis PING passed before export and after restore |
| Data check | `redis-cli GET` returned the exact seeded value after restore |
| Observed RPO | 0 seconds of lost writes in this one-record proof |
| Observed RTO | 1.519 seconds from restore start to verified content |
| Write-to-snapshot interval | 0.370 seconds |
| Cleanup | No proof containers, volumes, networks or temporary export remained |

`make validate` passed with three managed stack contracts on the same evaluation
host. The existing Dozzle `make lab-proof` also passed after the functional
verifier gained Redis PING support. These observations do not establish a
Production RPO/RTO or a private restore drill. The CI job runs the same
disposable proof on each proposed change.

Redis documents `SAVE` as a synchronous RDB snapshot and recommends `BGSAVE`
for normal Production use. This tiny proof intentionally uses `SAVE` so the
snapshot completion point is unambiguous; it is not a Production backup plan.
See [Redis `SAVE`](https://redis.io/docs/latest/commands/save/) and
[Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/).
