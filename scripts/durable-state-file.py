#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
from pathlib import Path


class DurableStateError(RuntimeError):
    pass


def fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def commit_file(source: Path, destination: Path, mode: int, fail_before_rename: bool) -> None:
    if not source.is_file():
        raise DurableStateError(f"source is not a regular file: {source}")
    if not destination.is_absolute():
        raise DurableStateError(f"destination must be absolute: {destination}")

    parent = destination.parent
    if not parent.is_dir():
        raise DurableStateError(f"destination parent is unavailable: {parent}")

    payload = source.read_bytes()
    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=parent)
    temp = Path(temp_name)
    try:
        os.fchmod(fd, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(fd, payload[offset:])
            if written <= 0:
                raise DurableStateError("short write while persisting state")
            offset += written
        os.fsync(fd)
        os.close(fd)
        fd = -1

        if fail_before_rename:
            raise DurableStateError("injected failure before atomic rename")

        os.replace(temp, destination)
        fsync_directory(parent)
    except Exception:
        if fd >= 0:
            os.close(fd)
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        raise


def remove_file(path: Path) -> None:
    if not path.is_absolute():
        raise DurableStateError(f"path must be absolute: {path}")
    try:
        path.unlink()
    except FileNotFoundError:
        return
    fsync_directory(path.parent)


def parse_mode(raw: str) -> int:
    try:
        mode = int(raw, 8)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("mode must be octal") from exc
    if mode < 0 or mode > 0o777:
        raise argparse.ArgumentTypeError("mode must be between 0000 and 0777")
    return mode


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    commit = sub.add_parser("commit")
    commit.add_argument("--source", required=True, type=Path)
    commit.add_argument("--destination", required=True, type=Path)
    commit.add_argument("--mode", required=True, type=parse_mode)
    commit.add_argument("--test-fail-before-rename", action="store_true")

    remove = sub.add_parser("remove")
    remove.add_argument("--path", required=True, type=Path)

    args = parser.parse_args()

    try:
        if args.command == "commit":
            commit_file(
                args.source,
                args.destination,
                args.mode,
                args.test_fail_before_rename,
            )
        else:
            remove_file(args.path)
    except DurableStateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: durable state operation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
