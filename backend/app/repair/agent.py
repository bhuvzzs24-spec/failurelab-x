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
lock=asyncio.Lock()
@app.post('/verify',response_model=VerificationReport)
async def verify(body:VerifyRequest,authorization:str=Header(default='')):
    token=os.getenv('REPAIR_AGENT_TOKEN','')
    if not token or not hmac.compare_digest(authorization,'Bearer '+token): raise HTTPException(401,'invalid agent token')
    try: validate(body.source)
    except (ValueError,SyntaxError): raise HTTPException(422,'unsupported patch')
    if not shutil.which('docker'): return VerificationReport(outcome='INFRASTRUCTURE_ERROR',candidate_id=str(body.candidate_id),reason='Docker executable is unavailable.')
    if lock.locked(): raise HTTPException(409,'verification agent busy')
    async with lock:
        name='failurelab-verify-'+uuid.uuid4().hex
        with tempfile.TemporaryDirectory(prefix='failurelab-agent-') as folder:
            path=Path(folder); path.chmod(0o755)
            (path/'input.json').write_text(body.model_dump_json()); (path/'input.json').chmod(0o444)
            command=['docker','run','--name',name,'--rm','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','1','--memory','512m','--pids-limit','64','--user','10001:10001','--tmpfs','/tmp:rw,nosuid,nodev,size=128m,mode=1777','--mount','type=bind,src='+str(path/'input.json')+',dst=/input.json,readonly','failurelab-verifier:phase3']
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
