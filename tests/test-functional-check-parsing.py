#!/usr/bin/env python3
"""Focused unit tests for functional-check contract parsing.

These tests document the accepted functional-check contract shape and the
important rejection cases for both parsers that consume
``stack_functional_checks``:

* the contract validator (``scripts/validate-stack-contracts.py``), which runs
  during ``make validate`` and the deployment/rollback boundary;
* the runtime verifier (``scripts/verify-compose-health.py``), which parses each
  check before probing a container.

All fixtures are synthetic and environment-neutral: no real hostnames, IP
addresses, credentials, private paths, or Production evidence are used.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "scripts" / "validate-stack-contracts.py"
VERIFIER = REPO / "scripts" / "verify-compose-health.py"


def _load(module_path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validator():
    return _load(VALIDATOR, "stack_contract_validator")


def load_verifier():
    return _load(VERIFIER, "compose_health_verifier")


def build_stack_with_checks(validator, test_root: Path, functional_checks) -> Path:
    """Copy the synthetic dozzle stack and swap in the given functional checks."""
    stack_dir = test_root / "stacks" / "dozzle"
    shutil.copytree(REPO / "stacks" / "dozzle", stack_dir)
    validator.ROOT = test_root
    contract_path = stack_dir / "stack.yml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    contract["stack_functional_checks"] = functional_checks
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    return stack_dir


def check_contract(validator, functional_checks, expect_error: str | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="blueprint-fcheck-test.") as raw_tmp:
        test_root = Path(raw_tmp)
        stack_dir = build_stack_with_checks(validator, test_root, functional_checks)
        if expect_error is None:
            validator.validate_stack(stack_dir)
            return
        try:
            validator.validate_stack(stack_dir)
        except validator.ContractError as exc:
            if expect_error not in str(exc):
                raise AssertionError(f"unexpected validation error: {exc}") from exc
        else:
            raise AssertionError("invalid functional check contract was accepted")


def expect_verification_error(verifier, raw, index, substring=None, error_type=None) -> None:
    try:
        result = verifier.validate_check(raw, index)
    except Exception as exc:  # noqa: BLE001 - we assert on the raised error
        if error_type is not None and not isinstance(exc, error_type):
            raise AssertionError(f"unexpected error type {type(exc).__name__}: {exc}") from exc
        if substring is not None and substring not in str(exc):
            raise AssertionError(f"unexpected verification error: {exc}") from exc
        return
    raise AssertionError(f"invalid functional check was accepted; returned {result!r}")


def valid_runtime_check(**overrides: object) -> dict:
    base = {
        "name": "dozzle-http",
        "service": "dozzle",
        "port": 8080,
        "status_codes": [200],
    }
    base.update(overrides)
    return base


def main() -> int:
    validator = load_validator()
    verifier = load_verifier()

    # --- Contract validator: accepted shape -----------------------------------
    # Minimal valid functional check (name + service + status_codes).
    check_contract(
        validator,
        [{"name": "dozzle-http", "service": "dozzle", "status_codes": [200]}],
    )

    # All supported contract fields are accepted; extra runtime-only fields
    # (port, path) are tolerated by the contract step and validated later.
    check_contract(
        validator,
        [
            {
                "name": "dozzle-http",
                "service": "dozzle",
                "port": 8080,
                "path": "/",
                "status_codes": [200, 301],
            }
        ],
    )

    # --- Contract validator: missing / malformed top-level --------------------
    check_contract(validator, None, "functional checks must be a non-empty list")
    check_contract(validator, [], "functional checks must be a non-empty list")
    check_contract(validator, ["not-a-mapping"], "must be a mapping")

    # --- Contract validator: missing / invalid required fields ---------------
    check_contract(
        validator,
        [{"service": "dozzle", "status_codes": [200]}],
        "invalid or duplicate functional check name",
    )
    check_contract(
        validator,
        [{"name": 123, "service": "dozzle", "status_codes": [200]}],
        "invalid or duplicate functional check name",
    )
    check_contract(
        validator,
        [{"name": "", "service": "dozzle", "status_codes": [200]}],
        "invalid or duplicate functional check name",
    )
    # Public/private boundary: a name must not carry a path separator.
    check_contract(
        validator,
        [{"name": "a/b", "service": "dozzle", "status_codes": [200]}],
        "invalid or duplicate functional check name",
    )
    # Duplicate (conflicting) declaration.
    check_contract(
        validator,
        [
            {"name": "dozzle-http", "service": "dozzle", "status_codes": [200]},
            {"name": "dozzle-http", "service": "dozzle", "status_codes": [200]},
        ],
        "invalid or duplicate functional check name",
    )

    check_contract(
        validator,
        [{"name": "dozzle-http", "status_codes": [200]}],
        "references an unknown service",
    )
    # Misspelled field is treated as a missing service.
    check_contract(
        validator,
        [{"name": "dozzle-http", "servce": "dozzle", "status_codes": [200]}],
        "references an unknown service",
    )
    # Service not declared in stack_expected_services.
    check_contract(
        validator,
        [{"name": "dozzle-http", "service": "postgres", "status_codes": [200]}],
        "references an unknown service",
    )
    # Wrong service type.
    check_contract(
        validator,
        [{"name": "dozzle-http", "service": 5, "status_codes": [200]}],
        "references an unknown service",
    )

    check_contract(
        validator,
        [{"name": "dozzle-http", "service": "dozzle"}],
        "has invalid status codes",
    )
    check_contract(
        validator,
        [{"name": "dozzle-http", "service": "dozzle", "status_codes": "200"}],
        "has invalid status codes",
    )
    check_contract(
        validator,
        [{"name": "dozzle-http", "service": "dozzle", "status_codes": []}],
        "has invalid status codes",
    )
    check_contract(
        validator,
        [{"name": "dozzle-http", "service": "dozzle", "status_codes": [200, "x"]}],
        "has invalid status codes",
    )
    check_contract(
        validator,
        [{"name": "dozzle-http", "service": "dozzle", "status_codes": [99]}],
        "has invalid status codes",
    )
    check_contract(
        validator,
        [{"name": "dozzle-http", "service": "dozzle", "status_codes": [600]}],
        "has invalid status codes",
    )
    # bool is a subclass of int; True must be rejected as a status code.
    check_contract(
        validator,
        [{"name": "dozzle-http", "service": "dozzle", "status_codes": [True]}],
        "has invalid status codes",
    )

    # --- Runtime verifier: accepted shape ------------------------------------
    parsed = verifier.validate_check(
        valid_runtime_check(), 1
    )
    assert parsed["name"] == "dozzle-http"
    assert parsed["service"] == "dozzle"
    assert parsed["port"] == 8080
    assert parsed["status_codes"] == [200]

    # --- Runtime verifier: invalid fields ------------------------------------
    expect_verification_error(
        verifier, valid_runtime_check(name="a/b"), 1, "unsafe check name"
    )
    expect_verification_error(
        verifier, valid_runtime_check(service="../x"), 1, "unsafe service"
    )
    expect_verification_error(
        verifier, valid_runtime_check(port="8080"), 1, "invalid port"
    )
    expect_verification_error(
        verifier, valid_runtime_check(port=True), 1, "invalid port"
    )
    expect_verification_error(
        verifier, valid_runtime_check(port=0), 1, "invalid port"
    )
    expect_verification_error(
        verifier, valid_runtime_check(port=65536), 1, "invalid port"
    )
    # Path must be an absolute HTTP path (starts with "/").
    expect_verification_error(
        verifier, valid_runtime_check(path="relative"), 1, "invalid path"
    )
    expect_verification_error(
        verifier,
        valid_runtime_check(status_codes=[200, "x"]),
        1,
        "invalid status_codes",
    )
    expect_verification_error(
        verifier, valid_runtime_check(status_codes=[99]), 1, "invalid status_codes"
    )
    # bool is a subclass of int; True must be rejected as a status code.
    expect_verification_error(
        verifier, valid_runtime_check(status_codes=[True]), 1, "invalid status_codes"
    )
    # Non-string body_regex must be rejected before re.compile is called.
    expect_verification_error(
        verifier, valid_runtime_check(body_regex=123), 1, "body_regex must be a string"
    )
    # An invalid body_regex fails to compile.
    expect_verification_error(
        verifier, valid_runtime_check(body_regex="("), 1, error_type=re.error
    )

    print("Functional-check parsing unit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
