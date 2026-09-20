#!/usr/bin/env bash
# Source-only helper for host-global deployment serialization.

homelab_acquire_global_lock() {
  local lock_file="$1"

  [[ "$lock_file" == /* ]] || {
    printf 'ERROR: lock path must be absolute: %s\n' "$lock_file" >&2
    return 2
  }

  if [[ ! -e "$lock_file" ]]; then
    (
      umask 000
      set -o noclobber
      : >"$lock_file"
    ) 2>/dev/null || true
  fi

  [[ -f "$lock_file" && ! -L "$lock_file" ]] || {
    printf 'ERROR: lock path is not a regular non-symlink file: %s\n' "$lock_file" >&2
    return 1
  }
  [[ -r "$lock_file" && -w "$lock_file" ]] || {
    printf 'ERROR: lock file is not shared-readable/writable: %s\n' "$lock_file" >&2
    return 1
  }

  exec {HOMELAB_DEPLOYMENT_LOCK_FD}>"$lock_file"
  if ! flock -n "$HOMELAB_DEPLOYMENT_LOCK_FD"; then
    return 75
  fi
}
