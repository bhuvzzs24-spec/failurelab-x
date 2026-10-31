import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import get_db
from app.models.entities import Project
from app.schemas.contracts import ServiceCreate
from conftest import RULE

@pytest.fixture
def client(sessions):
    def override():
        with sessions() as db: yield db
    app.dependency_overrides[get_db]=override
    from app.core.config import settings
    with TestClient(app,headers={"Authorization":"Bearer "+settings().api_token}) as client: yield client
    app.dependency_overrides.clear()

def test_api_persistence_graph_validation(client,sessions):
    assert client.get("/api/v1/projects",headers={"Authorization":"bad"}).status_code==401
    result=client.post("/api/v1/projects",json={"name":"test"}); assert result.status_code==201
    project=result.json()["id"]
    with sessions() as db: assert db.get(Project,project).name=="test"
    assert client.post("/api/v1/projects",json={"name":"test"}).status_code==409
    assert client.get("/api/v1/projects?limit=101").status_code==422
    assert client.post(f"/api/v1/projects/{project}/services",json={"name":"https://example.com","version":"1"}).status_code==422
    ids={}
    for name in ("gateway","order","payment","inventory"):
        r=client.post(f"/api/v1/projects/{project}/services",json={"name":name,"version":"1"}); assert r.status_code==201; ids[name]=r.json()["id"]
    r=client.post(f"/api/v1/projects/{project}/dependencies",json={"source_id":ids["gateway"],"target_id":ids["payment"],"kind":"http","operation":"/charge","workflow":"checkout"}); assert r.status_code==201
    graph=client.get(f"/api/v1/projects/{project}/graph").json()
    assert len(graph["nodes"])==4 and len(graph["edges"])==1
    invariant=client.post(f"/api/v1/projects/{project}/invariants",json={"name":"paid implies finalized","rule":RULE}); assert invariant.status_code==201
    exp=client.post(f"/api/v1/projects/{project}/experiments",json={"name":"discovery","config":{"fault":{"kind":"latency"},"invariant_ids":[invariant.json()["id"]]}}); assert exp.status_code==201
    path=f"/api/v1/experiments/{exp.json()['id']}/runs"
    r=client.post(path,json={"idempotency_key":"one"}); assert r.status_code==202
    run_id=r.json()["id"]
    assert client.post(path,json={"idempotency_key":"one"}).json()["id"]==run_id
    assert client.post(f"/api/v1/runs/{run_id}/cancel").json()["cancel_requested"]==1
    assert client.get(f"/api/v1/runs/{run_id}/summary").status_code==200
    assert client.get(path+"?status=CREATED").json()["total"]==1

def test_openapi(client):
    schema=client.get("/openapi.json").json()
    assert "RunSummary" in schema["components"]["schemas"]
    assert schema["paths"]["/api/v1/runs/{run_id}/summary"]["get"]["responses"]["200"]

def test_request_size_and_ssrf_rejection(client):
    from app.core.config import Settings
    from dataclasses import replace
    assert client.post("/api/v1/projects",content=b"x"*65537,headers={"Content-Type":"application/json"}).status_code==413
    with pytest.raises(ValueError): replace(Settings(),payment="http://169.254.169.254")
    with pytest.raises(ValueError): replace(Settings(),gateway="https://example.com")
    with pytest.raises(ValueError): replace(Settings(),payment="http://payment/redirect?url=outside")
