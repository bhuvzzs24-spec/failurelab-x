"""Privately prepare actual API read models. No network, provisioning or publishing.

Input must be an operator-reviewed synthetic public snapshot. The output remains
ignored: deploying it requires separate approval to upload evidence to Vercel.
"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import tempfile
import time

def prepare(source: Path, output: Path, *, reviewed=False):
    if not reviewed: raise ValueError('Explicit local snapshot review is required')
    raw=source.read_bytes()
    if len(raw)>24*1024*1024:raise ValueError('Snapshot is too large')
    body=json.loads(raw)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.verification.public_snapshot import import_snapshot,redact,canonical
    from app.core.db import Base,get_db
    # All HTTP calls below are in-process ASGI reads over this disposable database.
    # No readiness, execution or health adapter is invoked.
    from app.main import app
    from fastapi.testclient import TestClient
    from app.core.config import settings
    from app.core.security import Policy
    if Policy.load().mode!='local':raise ValueError('Preparation requires a local isolated operator process')
    resources={}
    with tempfile.TemporaryDirectory(prefix='failurelab-demo-export-') as folder:
        engine=create_engine('sqlite:///'+folder+'/snapshot.db',connect_args={'check_same_thread':False})
        Base.metadata.create_all(engine);import_snapshot(engine,raw,reviewed=True)
        sessions=sessionmaker(engine)
        def database():
            with sessions() as db:yield db
        app.dependency_overrides[get_db]=database
        client=TestClient(app,headers={'Authorization':'Bearer '+settings().api_token})
        def read(path):
            response=client.get('/'+path)
            if response.status_code!=200:raise ValueError('Recorded read failed: '+path)
            return response.json()
        def collection(path):
            rows=[];offset=0
            while True:
                page=read(path+f'?offset={offset}&limit=100');rows.extend(page['items']);offset=len(rows)
                if offset>=page['total']:break
                if not page['items']:raise ValueError('Incomplete source collection')
            resources[path]={'items':rows,'total':len(rows),'offset':0,'limit':100}
            return rows
        try:
            project=body['project_id'];base='api/v1/projects/'+project
            projects=collection('api/v1/projects')
            if len(projects)!=1 or projects[0]['name']!='FailureLab demo':raise ValueError('Only the managed synthetic demo is supported')
            for kind in ('services','invariants','experiments','runs','findings'):collection(base+'/'+kind)
            for kind in ('graph','overview'):resources[base+'/'+kind]=read(base+'/'+kind)
            for row in resources[base+'/runs']['items']:
                path='api/v1/runs/'+row['id']+'/summary';resources[path]=read(path)
            research='api/v1/research/projects/'+project
            jobs=collection(research+'/jobs')
            for kind in ('trials','findings','candidates'):collection(research+'/'+kind)
            for job in jobs:
                for kind in ('decisions','artifacts'):collection('api/v1/research/jobs/'+job['id']+'/'+kind)
        finally:
            client.close();app.dependency_overrides.pop(get_db,None);engine.dispose()
    def sanitize(value):
        value=redact(value)
        if isinstance(value,dict):
            result={k:sanitize(v) for k,v in value.items()}
            if {'payload','sha256','kind','id'}<=result.keys():
                result['payload']={**result['payload'],'frontend_demo_redaction':{'source_sha256':result['sha256'],'network_addresses_withheld':True}}
                result['sha256']=hashlib.sha256(canonical(result['payload'])).hexdigest()
            return result
        if isinstance(value,list):return [sanitize(item) for item in value]
        if isinstance(value,str):return re.sub(r'(?:https?|redis|rediss|postgresql)(?:\+psycopg)?://[^\s"\'<>\])}]+','[recorded sandbox endpoint withheld]',value)
        return value
    packet={'format':'failurelab-frontend-demo-v1','captured_at':time.time(),'source_revision':body['source_revision'],'source_snapshot_sha256':hashlib.sha256(raw).hexdigest(),'notice':'Curated recorded synthetic sandbox evidence. Counts and outcomes describe this captured dataset; live execution, service health and current traffic are unavailable.','resources':sanitize(resources)}
    encoded=canonical(packet)
    if len(encoded)>16*1024*1024:raise ValueError('Frontend recorded evidence exceeds 16 MiB')
    output.parent.mkdir(parents=True,exist_ok=True)
    descriptor=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'wb') as handle:handle.write(encoded)
    digest=hashlib.sha256(encoded).hexdigest();sidecar=Path(str(output)+'.sha256');sidecar.write_text(digest+'\n');sidecar.chmod(0o600)
    return {'bytes':len(encoded),'sha256':digest,'resource_count':len(resources),'captured_at':packet['captured_at'],'uploaded':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--snapshot',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--reviewed',action='store_true');args=parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:print(json.dumps(prepare(args.snapshot,args.output,reviewed=args.reviewed)))
    except (ValueError,OSError):raise SystemExit('Private demo preparation failed; no deployment or upload was attempted') from None
