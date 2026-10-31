import time
from sqlalchemy import select
from test_api import client
from app.models.entities import Run, Finding
from app.repositories.evidence import artifact

def test_project_aggregation_is_scoped_and_persistent(client,sessions,make_run):
    first=make_run(); second=make_run()
    with sessions.begin() as db:
        row=db.get(Run,first); row.status="RUNNING"
        experiment_id=row.experiment_id
        from app.models.entities import Experiment
        project_id=db.get(Experiment,experiment_id).project_id
        invariant_id=row.config["invariant_ids"][0]
        db.add(Finding(run_id=first,invariant_id=invariant_id,summary="asserted fixture finding",evidence={"status":"FAIL"}))
    with sessions() as db: artifact(db,first,"snapshot",{"state":{}})
    response=client.get(f"/api/v1/projects/{project_id}/overview")
    assert response.status_code==200
    data=response.json()
    assert data["service_count"]==4
    assert data["experiment_count"]==1
    assert data["run_count"]==1
    assert data["active_run_count"]==1
    assert data["violation_count"]==1
    assert data["artifact_count"]==1
    assert sum(point["runs"] for point in data["activity"])==1
    assert len(data["activity"])==14
    assert client.get(f"/api/v1/projects/{project_id}/runs?status=RUNNING").json()["total"]==1
    assert client.get(f"/api/v1/projects/{project_id}/runs?status=FAILED").json()["total"]==0
    assert client.get(f"/api/v1/projects/{project_id}/findings").json()["total"]==1
    assert client.get(f"/api/v1/projects/{project_id}/runs?status=INVALID").status_code==422
    assert client.get("/api/v1/projects/missing/overview").status_code==404

def test_capabilities_match_real_engine_and_exclude_secrets(client):
    response=client.get("/api/v1/capabilities")
    assert response.status_code==200
    data=response.json()
    assert data["max_fault_seconds"]==30
    assert data["max_run_seconds"]==90
    assert len(data["fault_kinds"])==6
    assert data["fault_targets"]==["payment"]
    assert not data["automatic_replay"] and not data["causal_analysis"]
    assert "token" not in str(data).lower() and "database_url" not in data
