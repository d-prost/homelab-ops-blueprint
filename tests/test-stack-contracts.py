#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "scripts" / "validate-stack-contracts.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("stack_contract_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load stack contract validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_contract_error(module, stack_dir: Path, message: str) -> None:
    try:
        module.validate_stack(stack_dir)
    except module.ContractError as exc:
        if message not in str(exc):
            raise AssertionError(f"unexpected validation error: {exc}") from exc
    else:
        raise AssertionError("invalid stack contract was accepted")


def main() -> int:
    module = load_validator()
    with tempfile.TemporaryDirectory(prefix="blueprint-contract-test.") as raw_tmp:
        test_root = Path(raw_tmp)
        stack_dir = test_root / "stacks" / "dozzle"
        shutil.copytree(REPO / "stacks" / "dozzle", stack_dir)
        module.ROOT = test_root
        module.validate_stack(stack_dir)

        manifest = stack_dir / "MANIFEST.tsv"
        original_manifest = manifest.read_text(encoding="utf-8")
        manifest.write_text(
            original_manifest.replace("docker-compose.yml", "unexpected-compose.yml"),
            encoding="utf-8",
        )
        expect_contract_error(module, stack_dir, "MANIFEST.tsv differs from stack.yml")
        manifest.write_text(original_manifest, encoding="utf-8")

        contract = stack_dir / "stack.yml"
        contract.write_text(
            contract.read_text(encoding="utf-8").replace(
                "    dest: defaults.env\n",
                "    dest: docker-compose.yml\n",
            ),
            encoding="utf-8",
        )
        expect_contract_error(module, stack_dir, "duplicate managed destination")

    print("Stack contract regression tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
