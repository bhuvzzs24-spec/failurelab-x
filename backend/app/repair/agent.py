"""Operator-run loopback agent. The worker has no Docker socket.

Only fixed image/entrypoint and literal policy data are accepted. No shell,
command, image, mount path or environment is accepted over this API.
"""
import asyncio
import hmac
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from pydantic import Field
from app.schemas.contracts import Contract
from app.schemas.research import Scenario, VerificationReport
from app.repair.patches import validate
class VerifyRequest(Contract):
    candidate_id: uuid.UUID
    source: str=Field(max_length=10000)
    scenario: Scenario
    base_sha256: str=Field(pattern=r'^[a-f0-9]{64}$')
    runtime_sha256: str|None=Field(None,pattern=r'^[a-f0-9]{64}$')
app=FastAPI(title='Restricted FailureLab repair agent')
from app.core.limits import BodyLimit
app.add_middleware(BodyLimit)
lock=asyncio.Lock()
@app.post('/verify',response_model=VerificationReport)
async def verify(body:VerifyRequest,authorization:str=Header(default='')):
    token=os.getenv('REPAIR_AGENT_TOKEN','')
    if (os.getenv('AGENT_REQUIRE_STRONG_TOKEN')=='1' and len(token)<32) or not token or not hmac.compare_digest(authorization.encode(),('Bearer '+token).encode()): raise HTTPException(401,'invalid agent token')
    try: validate(body.source)
    except (ValueError,SyntaxError): raise HTTPException(422,'unsupported patch')
    if not shutil.which('docker'): return VerificationReport(outcome='INFRASTRUCTURE_ERROR',candidate_id=str(body.candidate_id),reason='Docker executable is unavailable.')
    if lock.locked(): raise HTTPException(409,'verification agent busy')
    async with lock:
        name='failurelab-verify-'+uuid.uuid4().hex
        input_root=os.getenv('REPAIR_INPUT_ROOT')
        if input_root: Path(input_root).mkdir(parents=True,exist_ok=True,mode=0o700)
        with tempfile.TemporaryDirectory(prefix='failurelab-agent-',dir=input_root) as folder:
            path=Path(folder); path.chmod(0o755)
            (path/'input.json').write_text(body.model_dump_json()); (path/'input.json').chmod(0o444)
            host_file=path/'input.json'
            host_root=os.getenv('REPAIR_HOST_INPUT_ROOT')
            if host_root:
                if not input_root or not Path(host_root).is_absolute() or ',' in host_root: raise HTTPException(503,'invalid agent input mount configuration')
                host_file=Path(host_root)/path.relative_to(Path(input_root))/'input.json'
            command=['docker','run','--name',name,'--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','1','--memory','512m','--pids-limit','64','--user','10001:10001','--tmpfs','/tmp:rw,nosuid,nodev,size=128m,mode=1777','--mount','type=bind,src='+str(host_file)+',dst=/input.json,readonly','failurelab-verifier:phase3']
            process=None; inspect_process=None
            try:
                inspect_process=await asyncio.create_subprocess_exec('docker','image','inspect','failurelab-verifier:phase3','--format','{{.Id}}',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
                image_output,_=await asyncio.wait_for(inspect_process.communicate(),timeout=8)
                image_id=image_output.decode().strip()
                if inspect_process.returncode or not re.fullmatch(r'sha256:[a-f0-9]{64}',image_id): raise ValueError('verification image unavailable')
                command[-1]=image_id # execute the inspected immutable image, not a mutable tag
                process=await asyncio.create_subprocess_exec(*command,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
                output,_=await asyncio.wait_for(process.communicate(),timeout=90)
                if process.returncode or len(output)>4*1024*1024: raise ValueError('sandbox execution failed or exceeded output limit')
                report=VerificationReport.model_validate_json(output)
                report.environment={**report.environment,'verification_image_id':image_id,'container_limits':{'network':'none','cpus':1,'memory_mib':512,'pids':64,'read_only':True,'uid':10001}}
                return report
            except (OSError,ValueError,asyncio.TimeoutError):
                return VerificationReport(outcome='INFRASTRUCTURE_ERROR',candidate_id=str(body.candidate_id),reason='Restricted container failed, timed out, or returned invalid evidence.')
            finally:
                # Remove by agent-owned unique name even if client disconnects or command hangs.
                cleanup=await asyncio.create_subprocess_exec('docker','rm','--force',name,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
                try: await asyncio.wait_for(cleanup.wait(),timeout=8)
                except asyncio.TimeoutError: cleanup.kill(); await cleanup.wait()
                if process and process.returncode is None: process.kill(); await process.wait()
                if inspect_process and inspect_process.returncode is None: inspect_process.kill(); await inspect_process.wait()


@app.get('/health')
async def health(authorization:str=Header(default='')):
    token=os.getenv('REPAIR_AGENT_TOKEN','')
    if not token or not hmac.compare_digest(authorization.encode(),('Bearer '+token).encode()):raise HTTPException(401,'invalid agent token')
    if not shutil.which('docker'):raise HTTPException(503,'Docker unavailable')
    process=await asyncio.create_subprocess_exec('docker','image','inspect','failurelab-verifier:phase3',stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
    try:
        await asyncio.wait_for(process.wait(),timeout=3)
        if process.returncode:raise HTTPException(503,'verification image or daemon unavailable')
    except asyncio.TimeoutError:
        process.kill();await process.wait();raise HTTPException(503,'verification daemon timeout')
    return {'status':'ready','execution_scope':'restricted local verification image'}
