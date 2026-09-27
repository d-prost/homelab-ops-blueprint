# Synthetic Redis recovery boundary

This stack exists to prove the mechanics on a disposable target. It has no
published port, authentication, or Production credentials. Do not expose it on
an untrusted Docker network or adopt it directly as a Production service.

| Class | Location | Treatment |
| --- | --- | --- |
| Managed configuration | `compose.yaml`, `defaults.env`, `stack.yml` | Reviewed in Git; contains no credential |
| Persistent application data | Compose `redis_data` volume mounted at `/data` | Redis RDB export is required; never rolled back by configuration deployment |
| Generated runtime state | Redis process memory and temporary RDB files | Never committed to Git |
| Secrets | None in this synthetic example | Real credentials must be supplied outside Git |

The disposable proof seeds one deterministic key, runs Redis `SAVE`, copies the
resulting `dump.rdb` after checking that the source container and volume exist,
destroys the source volume, imports the RDB into a fresh named volume, and
checks the key with `redis-cli GET`. There are no optional backup inputs. A
missing required source fails before `SAVE` or export-file creation.

The proof reports observed RPO as zero lost writes because the latest seeded
record survives the restore. It reports observed RTO from the start of isolated
restore to a successful `GET`, plus the write-to-snapshot interval. These are
measurements on the disposable runner, not Production objectives. The proof
keeps no backup after cleanup. Configuration rollback never restores or rewinds
Redis data.

For a real deployment, use `docs/RECOVERY_READINESS.md` and a private restore
drill. In particular, prove compatibility when a candidate changes the data
format or schema before claiming that returning to the previous configuration
is safe.
