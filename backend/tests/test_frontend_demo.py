"""Offline preparation is a read-only computation over an actual fixture database."""
import hashlib
import importlib.util
import json
from pathlib import Path
import httpx
import pytest
from app.models.entities import Project,Run,Artifact
from app.verification.public_snapshot import canonical,export_snapshot

ROOT=Path(__file__).resolve().parents[2]
def preparer():
    spec=importlib.util.spec_from_file_location('prepare_recorded_demo',ROOT/'scripts/prepare_frontend_demo.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module.prepare

def test_frontend_export_reads_authoritative_records_without_network(sessions,make_run,tmp_path,monkeypatch):
    identity=make_run()
    with sessions.begin() as db:
        run=db.get(Run,identity);run.status='COMPLETED'
        project=db.query(Project).one();project.name='FailureLab demo';project_id=project.id
        payload={'actual':'unit fixture','endpoint':'http://127.0.0.1:1234/charge','password':'fixture-secret'}
        db.add(Artifact(run_id=identity,kind='snapshot',payload=payload,sha256=hashlib.sha256(canonical(payload)).hexdigest()))
    source=tmp_path/'source.json';source.write_bytes(export_snapshot(sessions.kw['bind'],project_id,'a'*40))
    def no_network(*args,**kwargs):raise AssertionError('Frontend preparation must not contact any external API')
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',no_network)
    output=tmp_path/'private/recorded.json';result=preparer()(source,output,reviewed=True)
    raw=output.read_bytes();packet=json.loads(raw)
    assert result['uploaded'] is False and result['sha256']==hashlib.sha256(raw).hexdigest()
    assert b'127.0.0.1' not in raw and b'fixture-secret' not in raw
    assert packet['resources']['api/v1/projects/'+project_id+'/overview']['run_count']==1
    assert packet['resources']['api/v1/runs/'+identity+'/summary']['run']['status']=='COMPLETED'
    assert output.stat().st_mode & 0o777==0o600
    with pytest.raises(FileExistsError):preparer()(source,output,reviewed=True)
    assert output.read_bytes()==raw
    with sessions() as db:assert db.query(Artifact).one().payload['password']=='fixture-secret'

def test_frontend_export_requires_review_before_reading_any_source(tmp_path):
    with pytest.raises(ValueError,match='review'):preparer()(tmp_path/'not-read.json',tmp_path/'not-written.json')
    assert not (tmp_path/'not-written.json').exists()
