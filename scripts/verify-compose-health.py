#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, socket, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path
import yaml
SAFE_SERVICE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"); SAFE_CHECK_NAME=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_. -]*$")
class VerificationError(RuntimeError): pass
def run(argv:list[str])->str:
    try: r=subprocess.run(argv,check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc: raise VerificationError(exc.stderr.strip() or exc.stdout.strip() or f"exit {exc.returncode}") from exc
    return r.stdout.strip()
def load_contract(path:Path)->dict:
    value=yaml.safe_load(path.read_text(encoding="utf-8"));
    if not isinstance(value,dict): raise VerificationError("stack contract must be a mapping")
    return value
def validate_check(raw:object,index:int)->dict:
    if not isinstance(raw,dict): raise VerificationError(f"functional check #{index} must be a mapping")
    name,service,port,path,codes,body=raw.get("name"),raw.get("service"),raw.get("port"),raw.get("path","/"),raw.get("status_codes",[200]),raw.get("body_regex")
    if not isinstance(name,str) or not SAFE_CHECK_NAME.fullmatch(name): raise VerificationError("unsafe check name")
    if not isinstance(service,str) or not SAFE_SERVICE.fullmatch(service): raise VerificationError(f"{name}: unsafe service")
    if not isinstance(port,int) or isinstance(port,bool) or not 1<=port<=65535: raise VerificationError(f"{name}: invalid port")
    protocol=raw.get("protocol","http")
    if protocol=="redis-ping":
        if any(field in raw for field in ("path","status_codes","body_regex")): raise VerificationError(f"{name}: Redis PING check contains HTTP fields")
        return {"name":name,"service":service,"port":port,"protocol":protocol}
    if protocol!="http": raise VerificationError(f"{name}: unsupported protocol")
    if not isinstance(path,str) or not path.startswith("/"): raise VerificationError(f"{name}: invalid path")
    if not isinstance(codes,list) or not codes or any(not isinstance(c,int) or isinstance(c,bool) or not 100<=c<=599 for c in codes): raise VerificationError(f"{name}: invalid status_codes")
    if body is not None:
        if not isinstance(body, str): raise VerificationError(f"{name}: body_regex must be a string")
        re.compile(body)
    return {"name":name,"service":service,"port":port,"path":path,"status_codes":codes,"body_regex":body,"protocol":protocol}
def addresses(compose:list[str],service:str)->list[str]:
    cid=run(compose+["ps","-q",service]);
    if not cid: raise VerificationError(f"{service}: no container ID")
    record=json.loads(run(["/usr/bin/docker","inspect",cid]))[0]; state=record.get("State",{})
    if state.get("Status")!="running": raise VerificationError(f"{service}: not running")
    if isinstance(state.get("Health"),dict) and state["Health"].get("Status")=="unhealthy": raise VerificationError(f"{service}: unhealthy")
    out=[n.get("IPAddress") for n in record.get("NetworkSettings",{}).get("Networks",{}).values() if isinstance(n,dict) and n.get("IPAddress")]
    if not out: raise VerificationError(f"{service}: no IPv4 address")
    return list(dict.fromkeys(out))
def verify(check:dict,addrs:list[str],attempts:int,delay:float,quiet:bool=False)->dict:
    pattern=re.compile(check["body_regex"]) if check["body_regex"] else None; errors=[]
    for attempt in range(attempts):
        errors=[]
        for addr in addrs:
            url=f"http://{addr}:{check['port']}{check['path']}"
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"homelab-ops-verifier/1"})
                with urllib.request.urlopen(req,timeout=4) as response: status=response.status; body=response.read(1024*1024).decode("utf-8",errors="replace")
            except (urllib.error.URLError,TimeoutError,OSError) as exc: errors.append(f"{url}: {exc}"); continue
            if status not in check["status_codes"]: errors.append(f"{url}: HTTP {status}"); continue
            if pattern and pattern.search(body) is None: errors.append(f"{url}: body mismatch"); continue
            if not quiet: print(f"PASS: {check['name']} service={check['service']} url={url} status={status}")
            return {"name":check["name"],"service":check["service"],"protocol":"http","status":"PASS","status_code":status}
        if attempt+1<attempts: time.sleep(delay)
    raise VerificationError(f"{check['name']}: failed: {'; '.join(errors)}")
def verify_redis_ping(check:dict,addrs:list[str],attempts:int,delay:float,quiet:bool=False)->dict:
    errors=[]
    for attempt in range(attempts):
        errors=[]
        for addr in addrs:
            try:
                with socket.create_connection((addr,check["port"]),timeout=4) as connection:
                    connection.sendall(b"*1\r\n$4\r\nPING\r\n")
                    response=connection.makefile("rb").readline(8)
                if response==b"+PONG\r\n":
                    if not quiet: print(f"PASS: {check['name']} service={check['service']} protocol=redis-ping")
                    return {"name":check["name"],"service":check["service"],"protocol":"redis-ping","status":"PASS"}
                errors.append(f"{addr}: unexpected Redis PING response")
            except (OSError,TimeoutError) as exc: errors.append(f"{addr}: {exc}")
        if attempt+1<attempts: time.sleep(delay)
    raise VerificationError(f"{check['name']}: failed: {'; '.join(errors)}")
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--stack-dir",type=Path,required=True); p.add_argument("--compose-file",required=True); p.add_argument("--env-file",required=True); p.add_argument("--contract",type=Path,required=True); p.add_argument("--project-name"); p.add_argument("--json",action="store_true"); p.add_argument("--attempts",type=int,default=15); p.add_argument("--delay",type=float,default=2.0); a=p.parse_args()
    contract=load_contract(a.contract); raw=contract.get("stack_functional_checks")
    if not isinstance(raw,list) or not raw: raise VerificationError("stack_functional_checks must be non-empty")
    compose=["/usr/bin/docker","compose","--env-file",str(a.stack_dir/a.env_file),"-f",str(a.stack_dir/a.compose_file)]
    if a.project_name: compose.extend(["-p",a.project_name])
    results=[]
    for i,item in enumerate(raw,1):
        check=validate_check(item,i)
        service_addresses=addresses(compose,check["service"])
        if check["protocol"]=="redis-ping": results.append(verify_redis_ping(check,service_addresses,a.attempts,a.delay,a.json))
        else: results.append(verify(check,service_addresses,a.attempts,a.delay,a.json))
    if a.json: print(json.dumps({"schema_version":1,"checks":results},sort_keys=True,separators=(",",":")))
    else: print(f"Functional verification passed for {len(raw)} check(s).")
    return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except (VerificationError,OSError,yaml.YAMLError,re.error,json.JSONDecodeError) as exc: print(f"ERROR: {exc}",file=sys.stderr); raise SystemExit(1)
