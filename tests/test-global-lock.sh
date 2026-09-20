#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck source=scripts/lock-utils.sh
source "$repo_root/scripts/lock-utils.sh"

tmp_root="$(mktemp -d)"
holder_pid=""
cleanup() {
  if [[ -n "$holder_pid" ]]; then
    kill "$holder_pid" >/dev/null 2>&1 || true
    wait "$holder_pid" >/dev/null 2>&1 || true
  fi
  rm -rf -- "$tmp_root"
}
trap cleanup EXIT
chmod 0777 "$tmp_root"

lock_file="$tmp_root/target-stack.lock"
ready_file="$tmp_root/ready"
holder_runtime="$tmp_root/runtime-holder"
contender_runtime="$tmp_root/runtime-contender"
mkdir -p "$holder_runtime" "$contender_runtime"
chmod 0700 "$holder_runtime" "$contender_runtime"

cat >"$tmp_root/holder.sh" <<'CHILD'
#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/lock-utils.sh
source "$REPO_ROOT/scripts/lock-utils.sh"
homelab_acquire_global_lock "$LOCK_FILE"
printf 'ready\n' >"$READY_FILE"
sleep 30 &
sleep_pid=$!
trap 'kill "$sleep_pid" >/dev/null 2>&1 || true; wait "$sleep_pid" >/dev/null 2>&1 || true; exit 0' TERM INT
wait "$sleep_pid"
CHILD

cat >"$tmp_root/contender.sh" <<'CHILD'
#!/usr/bin/env bash
set -Eeuo pipefail
# shellcheck source=scripts/lock-utils.sh
source "$REPO_ROOT/scripts/lock-utils.sh"
homelab_acquire_global_lock "$LOCK_FILE"
CHILD
chmod 0755 "$tmp_root/holder.sh" "$tmp_root/contender.sh"

env \
  REPO_ROOT="$repo_root" \
  LOCK_FILE="$lock_file" \
  READY_FILE="$ready_file" \
  XDG_RUNTIME_DIR="$holder_runtime" \
  bash "$tmp_root/holder.sh" &
holder_pid=$!

for _ in $(seq 1 100); do
  [[ -f "$ready_file" ]] && break
  kill -0 "$holder_pid" >/dev/null 2>&1 || {
    printf 'FAIL: lock holder exited before acquiring the lock.\n' >&2
    exit 1
  }
  sleep 0.05
done
[[ -f "$ready_file" ]] || {
  printf 'FAIL: lock holder did not become ready.\n' >&2
  exit 1
}

[[ "$(stat -c %a "$lock_file")" == "666" ]] || {
  printf 'FAIL: host-global lock must be shared-readable/writable.\n' >&2
  exit 1
}

# Same OS user, separate process, completely different runtime directory.
set +e
env \
  REPO_ROOT="$repo_root" \
  LOCK_FILE="$lock_file" \
  XDG_RUNTIME_DIR="$contender_runtime" \
  bash "$tmp_root/contender.sh"
same_user_rc=$?
set -e
((same_user_rc == 75)) || {
  printf 'FAIL: different runtime environment bypassed the same lock (rc=%s).\n' "$same_user_rc" >&2
  exit 1
}

# A second OS user must observe the same flock on the same control host.
set +e
sudo -u nobody flock -n "$lock_file" -c true
other_user_rc=$?
set -e
((other_user_rc != 0)) || {
  printf 'FAIL: a different OS user bypassed the host-global lock.\n' >&2
  exit 1
}

kill "$holder_pid"
wait "$holder_pid" || true
holder_pid=""

# The inherited descriptor intentionally keeps the lock while any holder child
# remains alive; once the holder process tree exits, the kernel releases it.
homelab_acquire_global_lock "$lock_file"

printf 'Host-global lock proof passed: different runtime environments and OS users serialize on one control host.\n'
