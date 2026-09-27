# Bounded multi-host rollout

`scripts/deploy-group.py` runs the existing single-target transaction once per
selected host. It does not create a distributed transaction or a distributed
lock. Each host keeps its own accepted record, result JSON and rollback state.

Define reusable groups in the private Ansible inventory. The stack mapping is
also private and lists the exact host aliases in deployment order:

```yaml
stacks:
  dozzle:
    group: web
    hosts: [web-a, web-b]
    canary: web-a
```

Each alias must belong to the declared group, and every selected host must
have a distinct expected hostname. The complete selection and Production SSH
policy are checked before the first host is changed. Copy the public mapping
example to `ansible/inventory/production/stack-targets.yml`, which Git ignores.

Run a read-only check across the group:

```bash
python3 scripts/deploy-group.py dozzle --check --mode serial
```

Deploy one host at a time in the listed order:

```bash
python3 scripts/deploy-group.py dozzle --mode serial
```

Canary mode requires `canary` to equal the first listed host. It deploys that
host, waits for its accepted transaction, then proceeds serially:

```bash
python3 scripts/deploy-group.py dozzle --mode canary
```

On the first failure, the wrapper skips every remaining host. Hosts already
accepted stay accepted; there is no automatic group-wide rollback. The group
result is `FAILED` if the first host failed, `PARTIAL` if at least one host
succeeded before failure, or `COMPLETE` when all succeed. A private JSON report
with one result per host is written under ignored `reports/` by default; use
`--output` to choose another path. The report records aliases and terminal
classes, never SSH addresses or credentials. Inspect the target's durable
record and unresolved marker before retrying a failed host. Re-running the
same group will revisit already accepted hosts through their normal
idempotent transaction path.

The wrapper accepts `--ref` for the same historical payload rules as
`deploy-stack.sh`. Production still requires a clean, current `main` control
plane and strict SSH host-key verification on every target. The host-global
lock applies independently to each target/stack pair on the one control host.

## Disposable two-target SSH proof

Before the code is merged to `main`, use two independent disposable Linux SSH
targets through the explicit Lab path. Keep the inventory and target mapping
outside public Git. Set `homelab_environment: lab`,
`ansible_connection: ssh`, each target's distinct
`homelab_expected_hostname`, and trusted SSH host keys. The group wrapper
rejects disabled host-key checking, unsafe SSH arguments, duplicate identities,
and hosts outside the mapped group. Both targets need Docker, Compose and
noninteractive privilege escalation for the deployment role.

```bash
python3 scripts/deploy-group.py dozzle \
  --environment lab \
  --inventory /private/hosts.yml \
  --targets /private/stack-targets.yml \
  --mode canary --check

python3 scripts/deploy-group.py dozzle \
  --environment lab \
  --inventory /private/hosts.yml \
  --targets /private/stack-targets.yml \
  --mode canary
```

The check must report `CHECK_PASSED` for both targets without creating managed
files. The deployment must accept the canary before starting the second host
and write `group_result: COMPLETE` with two `ACCEPTED` entries. Inspect each
target's accepted record, receipt and functional check independently. For the
negative proof, inject a candidate failure on the canary and verify that the
second target is `SKIPPED` and unchanged. Clean only the exact disposable
stack artifacts after capturing private evidence. The Lab path does not claim
Production authorization or weaken the Production `main` requirement.
