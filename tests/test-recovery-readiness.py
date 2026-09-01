#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "check-recovery-readiness.py"
NOW = "2026-09-01T23:00:00Z"
FRESH = "2026-09-01T21:00:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("recovery_readiness", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load recovery readiness module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def expect_error(module, callback, text: str) -> None:
    try:
        callback()
    except module.ReadinessError as exc:
        assert text in str(exc), exc
    else:
        raise AssertionError(f"expected ReadinessError containing: {text}")


def make_stack(stack_dir: Path) -> dict:
    (stack_dir / "recovery").mkdir(parents=True, exist_ok=True)
    (stack_dir / "compose.yaml").write_text(
        "services:\n  db:\n    image: ${DEMO_IMAGE}\n",
        encoding="utf-8",
    )
    (stack_dir / "defaults.env").write_text(
        f"DEMO_IMAGE=example.invalid/demo@sha256:{'1' * 64}\n",
        encoding="utf-8",
    )
    (stack_dir / "recovery" / "example.md").write_text(
        "# Synthetic restore runbook\n",
        encoding="utf-8",
    )
    return {
        "stack_compose_dest": "compose.yaml",
        "stack_expected_services": ["db"],
        "stack_functional_checks": [
            {
                "name": "api",
                "service": "db",
                "path": "/health",
                "status_codes": [200],
            }
        ],
        "stack_managed_files": [
            {"src": "compose.yaml", "dest": "compose.yaml", "mode": "0644"},
            {"src": "defaults.env", "dest": "defaults.env", "mode": "0644"},
        ],
        "operations": {
            "services": {
                "db": {
                    "stateful": True,
                    "persistent_mounts": [{"target": "/var/lib/example"}],
                    "backup": {"policy": "critical"},
                    "restore": {
                        "runbook": "recovery/example.md",
                        "verification": "functional",
                    },
                    "monitoring": {"required": True},
                }
            }
        },
    }


def make_evidence(module, stack_path: Path, observed_at: str = FRESH) -> dict:
    contract = module.recovery_proof_contract(stack_path)
    return {
        "schema_version": 1,
        "contract_hash": module.contract_hash(contract),
        "covered_services": sorted(contract["services"]),
        "disposition": "ready",
        "isolated_restore": {
            "passed": True,
            "functional_verification": True,
            "production_unchanged": True,
        },
        "backup_receipt": {"observed_at": observed_at},
    }


def validate(module, stack_path: Path, evidence_path: Path, public_root: Path):
    return module.validate_evidence(
        stack_path,
        evidence_path,
        10800,
        module.parse_utc(NOW, "test now"),
        current_contract_path=stack_path,
        forbidden_evidence_root=public_root,
    )


def main() -> int:
    module = load_module()
    with tempfile.TemporaryDirectory(prefix="blueprint-recovery-readiness.") as raw_tmp:
        root = Path(raw_tmp)
        public_root = root / "public"
        private_root = root / "private"
        stack_dir = public_root / "stacks" / "stateful-demo"
        stack_path = stack_dir / "stack.yml"
        evidence_path = private_root / "recovery-readiness.json"

        stack = make_stack(stack_dir)
        write_yaml(stack_path, stack)
        evidence = make_evidence(module, stack_path)
        write_json(evidence_path, evidence)

        result = validate(module, stack_path, evidence_path, public_root)
        assert result["ready"] is True
        assert result["stateful"] is True
        assert result["services"] == ["db"]
        assert result["backup_age_seconds"] == 7200

        stale = make_evidence(module, stack_path, "2026-09-01T18:00:00Z")
        write_json(evidence_path, stale)
        expect_error(
            module,
            lambda: validate(module, stack_path, evidence_path, public_root),
            "backup evidence is stale",
        )

        wrong_contract = make_evidence(module, stack_path)
        wrong_contract["contract_hash"] = "0" * 64
        write_json(evidence_path, wrong_contract)
        expect_error(
            module,
            lambda: validate(module, stack_path, evidence_path, public_root),
            "does not match the current public stack generation",
        )

        failed_restore = make_evidence(module, stack_path)
        failed_restore["isolated_restore"]["passed"] = False
        write_json(evidence_path, failed_restore)
        expect_error(
            module,
            lambda: validate(module, stack_path, evidence_path, public_root),
            "isolated_restore.passed must be true",
        )

        changed_production = make_evidence(module, stack_path)
        changed_production["isolated_restore"]["production_unchanged"] = False
        write_json(evidence_path, changed_production)
        expect_error(
            module,
            lambda: validate(module, stack_path, evidence_path, public_root),
            "isolated_restore.production_unchanged must be true",
        )

        incomplete_coverage = make_evidence(module, stack_path)
        incomplete_coverage["covered_services"] = ["other"]
        write_json(evidence_path, incomplete_coverage)
        expect_error(
            module,
            lambda: validate(module, stack_path, evidence_path, public_root),
            "does not cover the exact stateful service set",
        )

        not_ready = make_evidence(module, stack_path)
        not_ready["disposition"] = "not-ready"
        write_json(evidence_path, not_ready)
        expect_error(
            module,
            lambda: validate(module, stack_path, evidence_path, public_root),
            "disposition is not ready",
        )

        unknown_field = make_evidence(module, stack_path)
        unknown_field["snapshot_id"] = "synthetic-but-unsupported"
        write_json(evidence_path, unknown_field)
        expect_error(
            module,
            lambda: validate(module, stack_path, evidence_path, public_root),
            "contains unsupported field",
        )

        evidence = make_evidence(module, stack_path)
        write_json(evidence_path, evidence)
        (stack_dir / "defaults.env").write_text(
            f"DEMO_IMAGE=example.invalid/demo@sha256:{'2' * 64}\n",
            encoding="utf-8",
        )
        expect_error(
            module,
            lambda: validate(module, stack_path, evidence_path, public_root),
            "does not match the current public stack generation",
        )

        (stack_dir / "defaults.env").write_text(
            f"DEMO_IMAGE=example.invalid/demo@sha256:{'1' * 64}\n",
            encoding="utf-8",
        )
        before_monitoring = module.contract_hash(
            module.recovery_proof_contract(stack_path)
        )
        stack["operations"]["services"]["db"]["monitoring"]["required"] = False
        write_yaml(stack_path, stack)
        after_monitoring = module.contract_hash(
            module.recovery_proof_contract(stack_path)
        )
        assert before_monitoring == after_monitoring

        stack["operations"]["services"]["db"]["monitoring"]["required"] = True
        write_yaml(stack_path, stack)
        evidence = make_evidence(module, stack_path)
        write_json(evidence_path, evidence)

        in_tree_evidence = public_root / "private-evidence.json"
        write_json(in_tree_evidence, evidence)
        expect_error(
            module,
            lambda: validate(module, stack_path, in_tree_evidence, public_root),
            "outside the public repository tree",
        )

        evidence_path.chmod(0o666)
        expect_error(
            module,
            lambda: validate(module, stack_path, evidence_path, public_root),
            "must not be group- or world-writable",
        )
        evidence_path.chmod(0o600)

        historical_path = root / "historical" / "stack.yml"
        write_yaml(historical_path, {"stack_expected_services": ["db"]})
        expect_error(
            module,
            lambda: module.validate_evidence(
                historical_path,
                None,
                None,
                module.parse_utc(NOW, "test now"),
                current_contract_path=stack_path,
            ),
            "selected payload lacks a stateful recovery contract",
        )

        stateless_path = root / "stateless" / "stack.yml"
        write_yaml(stateless_path, {"stack_expected_services": ["demo"]})
        stateless = module.validate_evidence(
            stateless_path,
            None,
            None,
            module.parse_utc(NOW, "test now"),
        )
        assert stateless["stateful"] is False
        assert stateless["ready"] is True

    print(
        "Recovery readiness tests passed: exact generation binding, service coverage, "
        "freshness, isolation, evidence trust and historical bypass protections verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
