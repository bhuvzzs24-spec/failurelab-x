"""Operator-only export/import of recorded synthetic evidence. No execution adapter.

This module is never routed through the public API. Original private state is not
modified. A snapshot is review material, not authorization to publish it.
"""
import hashlib
import json
import re
import time
import uuid
from sqlalchemy import select
from app.models import entities, research
from app.core.db import Base

TABLES=('projects','services','dependencies','invariants','experiments','runs','artifacts','findings','research_jobs','research_trials','research_findings','research_decisions','repair_candidates','research_artifacts')
LIMIT=24*1024*1024
SECRET_KEY=re.compile(r'password|passwd|secret|authorization|api[_-]?key|access[_-]?token|control[_-]?token|private[_-]?key|database[_-]?url|broker[_-]?url',re.I)
TOKEN=re.compile(r'\b(?:gh[pousr]_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|sk-(?:proj-)?[a-zA-Z0-9_-]{25,})\b')
LOCAL_PATH=re.compile(r'(?:/(?:Users|home|private|tmp|srv|workspace|var)/[^\s"\'<>]+|[A-Z]:\\[^\s"\'<>]+)')

def redact(value,key=''):
    if SECRET_KEY.search(key):return '[redacted]'
    if isinstance(value,dict):return {k:redact(v,k) for k,v in value.items()}
    if isinstance(value,list):return [redact(v) for v in value]
    if isinstance(value,str):
        value=re.sub(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----','[redacted private key]',value)
        value=TOKEN.sub('[redacted token]',value)
        value=re.sub(r'(\w+(?:\+\w+)?://)[^\s/@]+:[^\s/@]+@',r'\1[redacted]@',value)
        return LOCAL_PATH.sub('[redacted local path]',value)
    return value

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def export_snapshot(engine,project_id,source_revision):
    uuid.UUID(project_id)
    tables=Base.metadata.tables;rows={}
    with engine.connect() as connection:
        project=connection.execute(select(tables['projects']).where(tables['projects'].c.id==project_id)).mappings().one_or_none()
        if not project or project['name']!='FailureLab demo':raise ValueError('Only the explicitly seeded synthetic demo project can be exported')
        for name in TABLES:
            table=tables[name]
            if name=='projects':query=select(table).where(table.c.id==project_id)
            elif name in ('artifacts','findings'):
                query=select(table).where(table.c.run_id.in_([row['id'] for row in rows['runs']]))
            elif name=='runs':query=select(table).where(table.c.experiment_id.in_([row['id'] for row in rows['experiments']]))
            elif name in ('research_decisions','research_artifacts'):query=select(table).where(table.c.job_id.in_([row['id'] for row in rows['research_jobs']]))
            else:query=select(table).where(table.c.project_id==project_id)
            rows[name]=[dict(row) for row in connection.execute(query).mappings()]
            if len(rows[name])>10000:raise ValueError('Snapshot exceeds bounded row count')
        if {row['name'] for row in rows['services']}!={'gateway','order','payment','inventory'}:raise ValueError('Managed demo registrations are incomplete')
        if any(row['status'] not in {'COMPLETED','FAILED','CANCELLED'} for name in ('runs','research_jobs') for row in rows[name]):raise ValueError('Wait for all executions to become terminal before export')
    for name in TABLES:
        rows[name]=redact(rows[name])
        if name in ('artifacts','research_artifacts'):
            for row in rows[name]:
                original=row['sha256'];row['payload']={**row['payload'],'public_snapshot_provenance':{'source_sha256':original,'redacted':True,'source_artifact_id':row['id']}}
                row['sha256']=hashlib.sha256(canonical(row['payload'])).hexdigest()
    manifest={'format':'failurelab-public-snapshot-v1','exported_at':time.time(),'source_revision':source_revision,'project_id':project_id,'scope':'Recorded synthetic sandbox observations; no live execution infrastructure','redacted':True,'audit_records_excluded':True,'review_required_before_publication':True,'tables':rows}
    encoded=canonical(manifest)
    if len(encoded)>LIMIT:raise ValueError('Snapshot exceeds 24 MiB')
    return encoded

def import_snapshot(engine,data,*,reviewed=False):
    if not reviewed:raise ValueError('Explicit review acknowledgement is required')
    if len(data)>LIMIT:raise ValueError('Snapshot exceeds 24 MiB')
    body=json.loads(data)
    if body.get('format')!='failurelab-public-snapshot-v1' or body.get('redacted') is not True or set(body.get('tables',{}))!=set(TABLES):raise ValueError('Unsupported snapshot manifest')
    project_id=body['project_id'];uuid.UUID(project_id);rows=body['tables'];tables=Base.metadata.tables
    if len(rows['projects'])!=1 or rows['projects'][0]['id']!=project_id or rows['projects'][0]['name']!='FailureLab demo':raise ValueError('Synthetic project manifest required')
    for name in TABLES:
        if not isinstance(rows[name],list) or len(rows[name])>10000:raise ValueError('Invalid snapshot row collection')
        for row in rows[name]:
            if set(row)!=set(tables[name].columns.keys()):raise ValueError('Snapshot columns differ from the migrated schema')
            if name in ('runs','research_jobs') and row['status'] not in {'COMPLETED','FAILED','CANCELLED'}:raise ValueError('Public snapshots cannot contain active execution records')
            if name in ('artifacts','research_artifacts') and hashlib.sha256(canonical(row['payload'])).hexdigest()!=row['sha256']:raise ValueError('Artifact integrity mismatch')
    # Only a fresh dedicated database is accepted. No replace/delete/update mode.
    with engine.begin() as connection:
        if connection.execute(select(tables['projects'].c.id).limit(1)).first():raise ValueError('Destination must be an empty dedicated snapshot database')
        for name in TABLES:
            if rows[name]:connection.execute(tables[name].insert(),rows[name])
    return {name:len(rows[name]) for name in TABLES}
