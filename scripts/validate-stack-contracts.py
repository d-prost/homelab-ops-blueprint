#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]; STACKS=ROOT/"stacks"; SAFE_STACK=re.compile(r"^[a-z0-9][a-z0-9-]*$"); SAFE_SERVICE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"); IMAGE=re.compile(r"^.+@sha256:[0-9a-f]{64}$")
class ContractError(RuntimeError): pass
def load(path:Path): return yaml.safe_load(path.read_text(encoding="utf-8"))
def main()->int:
    count=0
    for d in sorted(p for p in STACKS.iterdir() if p.is_dir()):
        s=d.name
        if not SAFE_STACK.fullmatch(s): raise ContractError(f"unsafe stack name: {s}")
        c,compose=load(d/"stack.yml"),load(d/"compose.yaml")
        if not isinstance(c,dict) or not isinstance(compose,dict): raise ContractError(f"{s}: YAML must be mappings")
        services,expected=compose.get("services"),c.get("stack_expected_services")
        if not isinstance(services,dict) or not isinstance(expected,list) or set(services)!=set(expected): raise ContractError(f"{s}: service contract mismatch")
        if any(not SAFE_SERVICE.fullmatch(str(x)) for x in expected): raise ContractError(f"{s}: unsafe service")
        checks=c.get("stack_functional_checks")
        if not isinstance(checks,list) or not checks or any(not isinstance(x,dict) or x.get("service") not in expected for x in checks): raise ContractError(f"{s}: invalid functional checks")
        lines=(d/"defaults.env").read_text(encoding="utf-8").splitlines(); images=[x.split("=",1)[1] for x in lines if x and not x.startswith("#") and "_IMAGE=" in x]
        if not images or any(not IMAGE.fullmatch(x) for x in images): raise ContractError(f"{s}: images must be pinned")
        count+=1
    print(f"Validated {count} managed stack contract(s)."); return 0
if __name__=="__main__": raise SystemExit(main())
