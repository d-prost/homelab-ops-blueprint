#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  printf 'Usage: %s REPO_ROOT COMMIT DEST [PATH ...]\n' "$0" >&2
}

if (($# < 3)); then
  usage
  exit 2
fi

repo_root="$1"
commit="$2"
dest="$3"
shift 3
paths=("$@")

[[ "$repo_root" == /* ]] || {
  printf 'ERROR: repository root must be absolute: %s\n' "$repo_root" >&2
  exit 2
}
[[ "$dest" == /* ]] || {
  printf 'ERROR: snapshot destination must be absolute: %s\n' "$dest" >&2
  exit 2
}
[[ ! -e "$dest" ]] || {
  printf 'ERROR: snapshot destination already exists: %s\n' "$dest" >&2
  exit 1
}

git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null
git -C "$repo_root" cat-file -e "${commit}^{commit}"
resolved_commit="$(git -C "$repo_root" rev-parse "${commit}^{commit}")"

for path in "${paths[@]}"; do
  [[ -n "$path" && "$path" != /* && "$path" != *"//"* ]] || {
    printf 'ERROR: unsafe snapshot path: %s\n' "$path" >&2
    exit 2
  }
  IFS='/' read -r -a path_parts <<<"$path"
  for part in "${path_parts[@]}"; do
    [[ "$part" != "." && "$part" != ".." && -n "$part" ]] || {
      printf 'ERROR: unsafe snapshot path: %s\n' "$path" >&2
      exit 2
    }
  done
  git -C "$repo_root" cat-file -e "${resolved_commit}:${path}" 2>/dev/null || {
    printf 'ERROR: path is unavailable at commit %s: %s\n' "$resolved_commit" "$path" >&2
    exit 1
  }
done

parent_dir="$(dirname -- "$dest")"
mkdir -p -- "$parent_dir"
tmp_dest="$(mktemp -d "${parent_dir}/.snapshot.XXXXXXXX")"
cleanup() {
  rm -rf -- "$tmp_dest"
}
trap cleanup EXIT

if ((${#paths[@]})); then
  git -C "$repo_root" archive "$resolved_commit" -- "${paths[@]}" | tar -x -C "$tmp_dest"
else
  git -C "$repo_root" archive "$resolved_commit" | tar -x -C "$tmp_dest"
fi

mv -- "$tmp_dest" "$dest"
trap - EXIT
printf '%s\n' "$resolved_commit"
