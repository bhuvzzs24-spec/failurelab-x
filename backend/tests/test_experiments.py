import asyncio
import hashlib
import json
import time
import httpx
import pytest
from sqlalchemy import select,update
from app.experiments.runner import Runner,recover,Busy
from app.models.entities import Run,Finding,Artifact,SandboxLease
from app.repositories.evidence import artifact

async def test_real_violation_and_evidence(sessions,make_run,sandbox):
    run_id=make_run()
    await Runner(sessions).run(run_id)
    with sessions() as db:
        run=db.get(Run,run_id)
        assert run.status=="COMPLETED",run.result
        findings=list(db.scalars(select(Finding).where(Finding.run_id==run_id)))
        assert len(findings)==1
        actual=findings[0].evidence["observed"]
        assert actual["payment"]["status"]=="charged"
        assert actual["order"]["status"]=="pending"
        assert actual["inventory"]["status"]=="reserved"
        artifacts=list(db.scalars(select(Artifact).where(Artifact.run_id==run_id)))
        assert {"manifest","snapshot","evaluation","cleanup","workflow"}<={a.kind for a in artifacts}
        for a in artifacts:
            assert hashlib.sha256(json.dumps(a.payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()==a.sha256
        assert db.get(SandboxLease,"demo").run_id is None
        import os
        destination=os.getenv("FAILURELAB_EVIDENCE_PATH")
        if destination:
            from pathlib import Path
            from app.schemas.contracts import RunOut, FindingOut, ArtifactOut
            payload={"run":RunOut.model_validate(run).model_dump(),"findings":[FindingOut.model_validate(f).model_dump() for f in findings],"artifacts":[ArtifactOut.model_validate(a).model_dump() for a in artifacts]}
            Path(destination).write_text(json.dumps(payload,indent=2))
    async with httpx.AsyncClient(trust_env=False,headers={"X-Control-Token":sandbox.control_token}) as client:
        assert (await client.get(sandbox.proxy_control+"/lease")).json()["active"] is None

async def test_no_false_finding_healthy(sessions,make_run,sandbox):
    run_id=make_run(delay=.01)
    await Runner(sessions).run(run_id)
    with sessions() as db:
        run=db.get(Run,run_id)
        assert run.status=="COMPLETED",run.result
        assert not list(db.scalars(select(Finding).where(Finding.run_id==run_id)))
        assert all(v["status"]=="PASS" for v in run.result["evaluations"].values())

async def test_missing_observation_is_inconclusive(sessions,make_run,sandbox,monkeypatch):
    from app.verification.observer import Observer
    original=Observer.snapshot
    calls=0
    async def missing(self,key):
        nonlocal calls
        state,errors=await original(self,key); calls+=1
        if calls>2:
            state.pop("payment",None); errors["payment"]="ReadTimeout"
        return state,errors
    monkeypatch.setattr(Observer,"snapshot",missing)
    run_id=make_run(); await Runner(sessions).run(run_id)
    with sessions() as db:
        run=db.get(Run,run_id); assert run.status=="COMPLETED",run.result
        assert all(v["status"]=="INCONCLUSIVE" for v in run.result["evaluations"].values())
        assert not list(db.scalars(select(Finding).where(Finding.run_id==run_id)))

async def test_cancellation_cleanup(sessions,make_run,sandbox):
    run_id=make_run(consistency=3)
    task=asyncio.create_task(Runner(sessions).run(run_id))
    for _ in range(200):
        await asyncio.sleep(.02)
        with sessions() as db:
            if db.scalar(select(Artifact).where(Artifact.run_id==run_id,Artifact.kind=="fault_schedule")):
                break
    else: pytest.fail("fault never activated")
    with sessions.begin() as db: db.get(Run,run_id).cancel_requested=1
    await task
    with sessions() as db: assert db.get(Run,run_id).status=="CANCELLED"
    async with httpx.AsyncClient(headers={"X-Control-Token":sandbox.control_token},trust_env=False) as client:
        assert (await client.get(sandbox.proxy_control+"/lease")).json()["active"] is None

async def test_timeout_and_recovery(sessions,make_run,sandbox):
    run_id=make_run(consistency=3)
    with sessions.begin() as db: db.get(Run,run_id).deadline=time.time()+.3
    await Runner(sessions).run(run_id)
    with sessions() as db:
        row=db.get(Run,run_id); assert row.status=="FAILED"; assert "deadline" in row.result["reason"]
    stale_id=make_run()
    Runner(sessions).claim(stale_id)  # emulate worker death after claiming, before cleanup
    async with httpx.AsyncClient(headers={"X-Control-Token":sandbox.control_token},trust_env=False) as client:
        response=await client.put(sandbox.proxy_control+"/lease",json={"execution_id":stale_id,"fault":{"kind":"http_503","duration_seconds":2}}); assert response.is_success
    with sessions.begin() as db: db.get(Run,stale_id).deadline=time.time()-1
    await recover(sessions)
    with sessions() as db:
        row=db.get(Run,stale_id); assert row.status=="FAILED"; assert row.result["cleanup_confirmed"]
        assert db.get(SandboxLease,"demo").run_id==stale_id
        assert db.get(SandboxLease,"demo").expires_at>time.time()

async def test_duplicate_delivery_and_sandbox_lock(sessions,make_run):
    first=make_run(); second=make_run()
    runner=Runner(sessions); assert runner.claim(first)
    assert runner.claim(first) is None
    with pytest.raises(Busy): runner.claim(second)

def test_artifact_bound(sessions,make_run):
    run_id=make_run()
    with sessions() as db:
        with pytest.raises(ValueError): artifact(db,run_id,"oversize",{"x":"x"*300000})

async def test_eventual_convergence_does_not_create_finding(sessions,make_run,sandbox):
    run_id=make_run(consistency=1)
    task=asyncio.create_task(Runner(sessions).run(run_id))
    try:
        for _ in range(200):
            await asyncio.sleep(.01)
            with sessions() as db:
                if db.get(Run,run_id).status=="VERIFYING": break
        else: pytest.fail("verification never started")
        await asyncio.sleep(.1)
        # A real retry repairs the workflow during the consistency window.
        async with httpx.AsyncClient(trust_env=False,headers={"X-Control-Token":sandbox.control_token,"X-Execution-ID":run_id},timeout=4) as client:
            response=await client.post(sandbox.gateway+"/checkout",json={"key":"fault_"+run_id.replace("-",""),"amount":100,"quantity":1})
            assert response.status_code==200
        await task
        with sessions() as db:
            row=db.get(Run,run_id); assert row.status=="COMPLETED",row.result
            assert all(e["status"]=="PASS" for e in row.result["evaluations"].values())
            assert not db.scalar(select(Finding).where(Finding.run_id==run_id))
    finally:
        if not task.done(): task.cancel()

async def test_queued_cancellation(sessions,make_run):
    run_id=make_run()
    with sessions.begin() as db: db.get(Run,run_id).cancel_requested=1
    await Runner(sessions).run(run_id)
    with sessions() as db:
        assert db.get(Run,run_id).status=="CANCELLED"
        assert db.get(SandboxLease,"demo").run_id is None

async def test_failed_baseline_never_creates_finding(sessions,make_run,sandbox,monkeypatch):
    from app.verification.observer import Observer
    async def missing(self,key): return {},{"payment":"ReadTimeout","order":"ReadTimeout","inventory":"ReadTimeout"}
    monkeypatch.setattr(Observer,"snapshot",missing)
    run_id=make_run(); await Runner(sessions).run(run_id)
    with sessions() as db:
        assert db.get(Run,run_id).status=="FAILED"
        assert not db.scalar(select(Finding).where(Finding.run_id==run_id))
        assert not db.scalar(select(Artifact).where(Artifact.run_id==run_id,Artifact.kind=="fault_schedule"))
