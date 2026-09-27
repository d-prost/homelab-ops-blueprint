#!/usr/bin/env bash
set -Eeuo pipefail
[[ "${HOMELAB_STATEFUL_PROOF:-0}" == 1 ]] || {
  echo 'Set HOMELAB_STATEFUL_PROOF=1 for the disposable Redis proof.' >&2
  exit 2
}

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
stack_dir="$repo_root/stacks/redis-synthetic"
compose=(docker compose --env-file "$stack_dir/defaults.env" -f "$stack_dir/compose.yaml")
image="$(sed -n 's/^REDIS_IMAGE=//p' "$stack_dir/defaults.env")"
[[ "$image" =~ ^redis@sha256:[0-9a-f]{64}$ ]] || {
  echo 'Redis image is not pinned by digest.' >&2
  exit 2
}

umask 077
proof_dir="$(mktemp -d "${TMPDIR:-/tmp}/homelab-redis-proof.XXXXXXXX")"
source_project="blueprint-redis-src-$$"
restore_project="blueprint-redis-restore-$$"
missing_project="blueprint-redis-missing-$$"
cleanup() {
  "${compose[@]}" -p "$source_project" down --volumes --remove-orphans >/dev/null 2>&1 || true
  "${compose[@]}" -p "$restore_project" down --volumes --remove-orphans >/dev/null 2>&1 || true
  docker volume rm "${restore_project}_redis_data" >/dev/null 2>&1 || true
  rm -rf -- "$proof_dir"
}
trap cleanup EXIT

required_backup_inputs() {
  local project="$1" container volume
  container="$("${compose[@]}" -p "$project" ps -q redis 2>/dev/null)"
  [[ -n "$container" ]] || { echo 'Required source container is missing.' >&2; return 1; }
  [[ "$(docker inspect -f '{{.State.Running}}' "$container")" == true ]] || {
    echo 'Required source container is not running.' >&2
    return 1
  }
  volume="${project}_redis_data"
  docker volume inspect "$volume" >/dev/null 2>&1 || {
    echo 'Required persistent volume is missing.' >&2
    return 1
  }
  "${compose[@]}" -p "$project" exec -T redis test -d /data || {
    echo 'Required Redis data directory is missing.' >&2
    return 1
  }
  [[ "$("${compose[@]}" -p "$project" exec -T redis redis-cli --raw EXISTS blueprint:record | tr -d '\r')" == 1 ]] || {
    echo 'Required representative record is missing.' >&2
    return 1
  }
}

wait_for_redis() {
  local project="$1" attempt
  for attempt in {1..30}; do
    if [[ "$("${compose[@]}" -p "$project" exec -T redis redis-cli --raw PING 2>/dev/null | tr -d '\r')" == PONG ]]; then
      return 0
    fi
    sleep 1
  done
  echo 'Redis did not become ready.' >&2
  return 1
}

seconds_between() {
  python3 - "$1" "$2" <<'PY'
import sys
print(f"{(int(sys.argv[2]) - int(sys.argv[1])) / 1_000_000_000:.3f}")
PY
}

# Exercise the same preflight before any source exists. No export may be created.
if required_backup_inputs "$missing_project" 2>"$proof_dir/missing.log"; then
  echo 'Missing required backup input was accepted.' >&2
  exit 1
fi
[[ ! -e "$proof_dir/dump.rdb" ]] || { echo 'Negative preflight created an export.' >&2; exit 1; }
grep -q 'Required source container is missing' "$proof_dir/missing.log"
echo 'Missing required backup input refused before export.'

"${compose[@]}" -p "$source_project" up -d --wait
wait_for_redis "$source_project"
python3 "$repo_root/scripts/verify-compose-health.py" \
  --stack-dir "$stack_dir" --compose-file compose.yaml --env-file defaults.env \
  --contract "$stack_dir/stack.yml" --project-name "$source_project" --attempts 3 --delay 1
[[ "$("${compose[@]}" -p "$source_project" exec -T redis redis-cli --raw SET blueprint:record synthetic-v1 | tr -d '\r')" == OK ]]
seed_ns="$(date +%s%N)"
required_backup_inputs "$source_project"
[[ "$("${compose[@]}" -p "$source_project" exec -T redis redis-cli --raw SAVE | tr -d '\r')" == OK ]]
snapshot_ns="$(date +%s%N)"
source_container="$("${compose[@]}" -p "$source_project" ps -q redis)"
docker cp "$source_container:/data/dump.rdb" "$proof_dir/dump.rdb"
[[ -s "$proof_dir/dump.rdb" ]]
export_sha="$(sha256sum "$proof_dir/dump.rdb" | cut -d' ' -f1)"

"${compose[@]}" -p "$source_project" down --volumes --remove-orphans
if docker volume inspect "${source_project}_redis_data" >/dev/null 2>&1; then
  echo 'Original application volume survived teardown.' >&2
  exit 1
fi

restore_start_ns="$(date +%s%N)"
"${compose[@]}" -p "$restore_project" up --no-start
docker run --rm \
  --mount "type=volume,src=${restore_project}_redis_data,dst=/data" \
  --mount "type=bind,src=${proof_dir},dst=/export,readonly" \
  "$image" sh -ec 'cp /export/dump.rdb /data/dump.rdb; chown redis:redis /data/dump.rdb'
"${compose[@]}" -p "$restore_project" up -d --wait
wait_for_redis "$restore_project"
python3 "$repo_root/scripts/verify-compose-health.py" \
  --stack-dir "$stack_dir" --compose-file compose.yaml --env-file defaults.env \
  --contract "$stack_dir/stack.yml" --project-name "$restore_project" --attempts 3 --delay 1
restored="$("${compose[@]}" -p "$restore_project" exec -T redis redis-cli --raw GET blueprint:record | tr -d '\r')"
[[ "$restored" == synthetic-v1 ]] || { echo 'Restored Redis record mismatch.' >&2; exit 1; }
restore_end_ns="$(date +%s%N)"

python3 - "$(seconds_between "$seed_ns" "$snapshot_ns")" "$(seconds_between "$restore_start_ns" "$restore_end_ns")" "$export_sha" <<'PY'
import json
import sys
print(json.dumps({
    "schema_version": 1,
    "result": "PASS",
    "representative_record": "blueprint:record",
    "observed_rpo_seconds": 0.0,
    "observed_rto_seconds": float(sys.argv[2]),
    "write_to_snapshot_seconds": float(sys.argv[1]),
    "export_sha256": sys.argv[3],
    "source_destroyed": True,
    "isolated_restore_verified": True,
}, sort_keys=True))
PY
