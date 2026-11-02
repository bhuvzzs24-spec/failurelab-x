import hashlib
import json
import pytest
from sqlalchemy import create_engine,select,func
from app.core.db import Base
from app.models.entities import Project,Service,Experiment,Run,Artifact
from app.verification.public_snapshot import export_snapshot,import_snapshot,canonical,redact

@pytest.fixture
def source(sessions):
    with sessions.begin() as db:
        project=Project(name='FailureLab demo');db.add(project);db.flush()
        for name in ('gateway','order','payment','inventory'):db.add(Service(project_id=project.id,name=name,version='unit fixture'))
        experiment=Experiment(project_id=project.id,name='Unit fixture',config={});db.add(experiment);db.flush()
        run=Run(experiment_id=experiment.id,idempotency_key='fixture',status='COMPLETED',deadline=1,config={});db.add(run);db.flush()
        payload={'state':{'payment':{'status':'charged'}},'password':'unit-only','path':'/Users/test/private.log'}
        db.add(Artifact(run_id=run.id,kind='snapshot',sha256=hashlib.sha256(canonical(payload)).hexdigest(),payload=payload));identity=project.id
    return sessions.kw['bind'],identity

def test_export_import_preserves_observations_and_recomputes_redacted_artifact_integrity(source,tmp_path):
    engine,project=source;data=export_snapshot(engine,project,'a'*40);body=json.loads(data)
    assert b'/Users/' not in data and b'unit-only' not in data
    artifact=body['tables']['artifacts'][0]
    assert artifact['payload']['state']['payment']['status']=='charged'
    assert hashlib.sha256(canonical(artifact['payload'])).hexdigest()==artifact['sha256']
    assert artifact['payload']['public_snapshot_provenance']['source_sha256']
    target=create_engine('sqlite:///'+str(tmp_path/'public.db'));Base.metadata.create_all(target)
    try:
        with pytest.raises(ValueError):import_snapshot(target,data)
        counts=import_snapshot(target,data,reviewed=True);assert counts['services']==4
        with target.connect() as connection:assert connection.execute(select(func.count()).select_from(Project)).scalar()==1
        with pytest.raises(ValueError):import_snapshot(target,data,reviewed=True)
        with engine.connect() as connection:assert connection.execute(select(Artifact.payload)).scalar()['password']=='unit-only' # original remains intact
    finally:target.dispose()

def test_snapshot_rejects_active_executions_and_tampered_artifacts(source,tmp_path):
    engine,project=source;data=export_snapshot(engine,project,'a'*40);body=json.loads(data);body['tables']['artifacts'][0]['payload']['state']={}
    target=create_engine('sqlite:///'+str(tmp_path/'public.db'));Base.metadata.create_all(target)
    try:
        with pytest.raises(ValueError,match='integrity'):import_snapshot(target,canonical(body),reviewed=True)
        with engine.begin() as connection:connection.execute(Run.__table__.update().values(status='RUNNING'))
        with pytest.raises(ValueError,match='terminal'):export_snapshot(engine,project,'a'*40)
    finally:target.dispose()

def test_redaction_preserves_operations_and_removes_nested_credentials():
    result=redact({'operation':'/charge','nested':{'authorization':'unit-only','count':2},'path':'/private/tmp/local.log'})
    assert result=={'operation':'/charge','nested':{'authorization':'[redacted]','count':2},'path':'[redacted local path]'}
