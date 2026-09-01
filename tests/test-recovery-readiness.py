#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "check-recovery-readiness.py"


def load_module():
    spec = importlib.util.spec_from_file_location("recovery_readiness", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load recovery readiness module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data) if path.suffix == ".json" else yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def expect_error(module, callback, text: str) -> None:
    try:
        callback()
    except module.ReadinessError as exc:
        assert text in str(exc), exc
    else:
        raise AssertionError(f"expected ReadinessError containing: {text}")


def main() -> int:
    module = load_module()
    with tempfile.TemporaryDirectory(prefix="blueprint-recovery-readiness.") as raw_tmp:
        root = Path(raw_tmp)
        stack_path = root / "stack.yml"
        evidence_path = root / "evidence.json"

        stack = {
            "operations": {
                "services": {
                    "db": {
                        "stateful": True,
                        "persistent_mounts": [{"target": "/var/lib/example"}],
                        "backup": {"policy": "critical"},
                        "restore": {"runbook": "recovery/example.md", "verification": "functional"},
                        "monitoring": {"required": True},
                    }
                }
            }
        }
        write(stack_path, stack)
        digest = module.contract_hash(module.stateful_recovery_contract(stack))
        evidence = {
            "schema_version": 1,
            "contract_hash": digest,
            "disposition": "ready",
            "isolated_restore": {"passed": True, "functional_verification": True},
            "backup_receipt": {"observed_at": "2026-09-01T21:00:00Z"},
        }
        write(evidence_path, evidence)

        result = module.validate_evidence(
            stack_path,
            evidence_path,
            10800,
            module.parse_utc("2026-09-01T23:00:00Z", "test now"),
        )
        assert result["ready"] is True
        assert result["stateful"] is True
        assert result["backup_age_seconds"] == 7200

        stale = dict(evidence)
        stale["backup_receipt"] = {"observed_at": "2026-09-01T18:00:00Z"}
        write(evidence_path, stale)
        expect_error(
            module,
            lambda: module.validate_evidence(
                stack_path,
                evidence_path,
                10800,
                module.parse_utc("2026-09-01T23:00:00Z", "test now"),
            ),
            "backup evidence is stale",
        )

        wrong_contract = dict(evidence)
        wrong_contract["contract_hash"] = "0" * 64
        write(evidence_path, wrong_contract)
        expect_error(
            module,
            lambda: module.validate_evidence(
                stack_path,
                evidence_path,
                10800,
                module.parse_utc("2026-09-01T23:00:00Z", "test now"),
            ),
            "does not match the current recovery contract",
        )

        failed_restore = dict(evidence)
        failed_restore["isolated_restore"] = {"passed": False, "functional_verification": True}
        write(evidence_path, failed_restore)
        expect_error(
            module,
            lambda: module.validate_evidence(
                stack_path,
                evidence_path,
                10800,
                module.parse_utc("2026-09-01T23:00:00Z", "test now"),
            ),
            "passed must be true",
        )

        not_ready = dict(evidence)
        not_ready["disposition"] = "not-ready"
        write(evidence_path, not_ready)
        expect_error(
            module,
            lambda: module.validate_evidence(
                stack_path,
                evidence_path,
                10800,
                module.parse_utc("2026-09-01T23:00:00Z", "test now"),
            ),
            "disposition is not ready",
        )

        stateless_path = root / "stateless.yml"
        write(stateless_path, {"stack_target_dir": "/srv/homelab-ops/example"})
        stateless_contract = module.stateful_recovery_contract(module.load_yaml(stateless_path))
        assert stateless_contract == {"services": {}}

    print("Recovery readiness tests passed: current evidence accepted; stale, mismatched, failed and not-ready evidence rejected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
