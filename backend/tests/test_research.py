import asyncio
import hashlib
import json
import time
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.models.research import ResearchJob,ResearchTrial,ResearchFinding,ResearchArtifact
from app.models.entities import Project,Service,SandboxLease
from app.schemas.research import SearchInput,ResearchCreate,Scenario,Action
from app.benchmarks.catalog import witness,DEFECTS
from app.benchmarks.executor import HTTPExecutor
from app.benchmarks.local import cluster
from app.planning.search import Planner,search
from app.minimization.reduce import minimize
from app.causal.investigate import investigate
from app.repair.patches import prepare,validate,POLICY_PATH
from app.verification.counterfactual import compare
from app.research.jobs import ResearchRunner,recover_research

@pytest.fixture(scope='module')
def research_cluster(tmp_path_factory):
    with cluster(tmp_path_factory.mktemp('research-http')) as connection: yield connection

@pytest.mark.parametrize('defect',DEFECTS)
async def test_real_http_defect_and_fixed_reference(research_cluster,defect):
    execute=HTTPExecutor(*research_cluster)
    original=await execute(witness(defect)); fixed=await execute(witness(defect),'reference')
    assert original['classification']=='APPLICATION_VIOLATION',original
    assert original['evidence']['fault_receipts']
    assert fixed['classification']=='NO_VIOLATION',fixed
    baseline=await execute(witness(defect).model_copy(update={'actions':[],'concurrency':1}))
    assert baseline['classification']=='NO_VIOLATION',baseline

async def test_unobserved_missing_and_infrastructure(research_cluster):
    execute=HTTPExecutor(*research_cluster)
    late=witness('payment_ack_loss').model_copy(update={'actions':[Action(boundary='charge',kind='latency',at_ms=500)]})
    assert (await execute(late))['classification']=='INJECTION_NOT_OBSERVED'
    urls,token=research_cluster
    broken=HTTPExecutor({**urls,'payment':'http://127.0.0.1:1'},token)
    assert (await broken(witness('payment_ack_loss')))['classification']=='INFRASTRUCTURE_ERROR'

async def test_equal_budgets_reproducible_planner():
    for strategy in ('random','coverage','adaptive'):
        config=SearchInput(strategy=strategy,budget=7,seed=17)
        a=Planner(config); b=Planner(config)
        assert [a.choose()[0].model_dump() for _ in range(4)]==[b.choose()[0].model_dump() for _ in range(4)]
        decisions=[]
        async def execute(s,variant='original'):
            return {'id':str(len(decisions)),'scenario':s.model_dump(),'signature':'one','classification':'APPLICATION_VIOLATION','cost_seconds':.5}
        report=await search(config,execute,lambda *args:decisions.append(args))
        assert report['executed']==7 and len(decisions)==7 and report['unique_violation_signatures']==1
        assert sum(d[4] for d in decisions)==1

async def test_reduction_and_flaky_rejection():
    original=witness('payment_ack_loss'); original.actions.append(Action(boundary='reserve',kind='http_503',phase='after'))
    calls=[]
    async def execute(s,variant='original'):
        Scenario.model_validate(s.model_dump()) # reductions must stay inside public fault bounds
        calls.append(s)
        hit=any(a.boundary=='charge' and a.delay_ms>=90 for a in s.actions)
        return {'id':str(len(calls)),'classification':'APPLICATION_VIOLATION' if hit else 'NO_VIOLATION','signature':'sig' if hit else None,'cost_seconds':.01}
    report=await minimize(original,'sig',execute,100,2)
    assert len(report.reduced.actions)==1 and report.reduced.amount==1
    assert report.local_minimality_tested and report.reproductions==2
    async def flaky(s,variant='original'):
        result=await execute(s); result['classification']='INCONCLUSIVE' if len(calls)%2 else 'APPLICATION_VIOLATION'; return result
    report=await minimize(original,'sig',flaky,20,2)
    assert report.reduced==original and not report.local_minimality_tested

async def test_causal_pairs_real_http(research_cluster):
    execute=HTTPExecutor(*research_cluster); s=witness('payment_ack_loss'); failure=await execute(s)
    report=await investigate(s,failure['signature'],execute,20,2)
    assert next(h for h in report['hypotheses'] if h['id']=='acknowledgement')['status']=='SUPPORTED'
    assert next(h for h in report['hypotheses'] if h['id']=='retry')['status']=='INCONCLUSIVE'
    assert all('confidence' not in h for h in report['hypotheses'])

def test_patch_rejects_code_and_isolates(tmp_path,monkeypatch):
    monkeypatch.setenv('REPAIR_WORKSPACE_ROOT',str(tmp_path))
    before=POLICY_PATH.read_text(); patch,details=prepare('payment_ack_loss')
    assert POLICY_PATH.read_text()==before and details['workspace_id'].startswith('candidate-')
    assert validate(details['source'])['payment_ack_loss'] is True
    assert (tmp_path/details['workspace_id']/'policies.py').exists()
    for source in ["import os\nPOLICIES={}","POLICIES=__import__('os').system('echo bad')","POLICIES={}"]:
        with pytest.raises((ValueError,SyntaxError)): validate(source)

async def test_independent_verification_detects_regression():
    async def original(s): return {'classification':'APPLICATION_VIOLATION','signature':'sig','cost_seconds':1,'evidence':{}}
    async def fixed(s): return {'classification':'NO_VIOLATION','signature':None,'cost_seconds':.5,'evidence':{}}
    assert (await compare('candidate',witness('payment_ack_loss'),original,fixed)).outcome=='PATCH_PASSES_TESTED_SCENARIOS'
    async def regressed(s):
        row=await fixed(s)
        if not s.actions: row['classification']='APPLICATION_VIOLATION'
        return row
    assert (await compare('candidate',witness('payment_ack_loss'),original,regressed)).outcome=='PATCH_FAILS_VERIFICATION'

@pytest.fixture
def research_job(sessions):
    def create(kind='SEARCH',**kwargs):
        with sessions.begin() as db:
            p=Project(name='research-'+str(time.time_ns())); db.add(p); db.flush()
            for name in ('gateway','order','payment','inventory'): db.add(Service(project_id=p.id,name=name,version='test'))
            if db.get(SandboxLease,'benchmark') is None: db.add(SandboxLease(id='benchmark',expires_at=0))
            config=ResearchCreate(kind=kind,idempotency_key='test',search=SearchInput(budget=2,defects=['payment_ack_loss']),**kwargs)
            j=ResearchJob(project_id=p.id,kind=kind,idempotency_key='test',input=config.model_dump(),deadline=time.time()+30); db.add(j); db.flush()
            return j.id,p.id
    return create

async def test_jobs_persist_evidence_deduplicate_cancel_recovery(sessions,research_job,research_cluster):
    identity,project=research_job(); runner=ResearchRunner(sessions,HTTPExecutor(*research_cluster)); await runner.run(identity)
    with sessions() as db:
        j=db.get(ResearchJob,identity); assert j.status=='COMPLETED',j.error
        assert len(list(db.scalars(select(ResearchTrial).where(ResearchTrial.job_id==identity))))==2
        artifacts=list(db.scalars(select(ResearchArtifact).where(ResearchArtifact.job_id==identity))); assert artifacts
        for a in artifacts: assert a.sha256==hashlib.sha256(json.dumps(a.payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    identity,_=research_job()
    with sessions.begin() as db: db.get(ResearchJob,identity).cancel_requested=1
    await runner.run(identity)
    with sessions() as db: assert db.get(ResearchJob,identity).status=='CANCELLED'
    identity,_=research_job()
    with sessions.begin() as db: row=db.get(ResearchJob,identity); row.status='RUNNING'; row.deadline=time.time()-1
    recover_research(sessions)
    with sessions() as db: assert db.get(ResearchJob,identity).status=='FAILED'

def test_research_api(sessions,research_job):
    from app.main import app
    from app.core.db import get_db
    identity,project=research_job()
    def database():
        with sessions() as db: yield db
    app.dependency_overrides[get_db]=database
    try:
        client=TestClient(app); headers={'Authorization':'Bearer local-development-token'}
        response=client.get('/api/v1/research/projects/'+project+'/jobs',headers=headers)
        assert response.status_code==200 and response.json()['total']==1
        body={'kind':'SEARCH','idempotency_key':'new','search':{'budget':2}}
        url='/api/v1/research/projects/'+project+'/jobs'
        created=client.post(url,json=body,headers=headers); assert created.status_code==202,created.text
        assert client.post(url,json=body,headers=headers).json()['id']==created.json()['id']
        assert client.post(url,json={**body,'search':{'budget':3}},headers=headers).status_code==409
        assert client.post(url,json={**body,'host':'http://example.com'},headers=headers).status_code==422
        assert client.post('/api/v1/research/jobs/'+created.json()['id']+'/cancel',json={},headers=headers).json()['status']=='CANCELLED'
        assert client.get(url).status_code==401
    finally: app.dependency_overrides.clear()

async def test_cancel_running_and_fence_stale_owner(sessions,research_job):
    identity,project=research_job()
    called=asyncio.Event(); release=asyncio.Event()
    async def controlled(s,variant='original'):
        called.set(); await release.wait()
        return {'id':'trial','scenario':s.model_dump(),'variant':variant,'classification':'NO_VIOLATION','signature':None,'cost_seconds':.01,'evidence':{}}
    task=asyncio.create_task(ResearchRunner(sessions,controlled).run(identity)); await called.wait()
    with sessions.begin() as db: db.get(ResearchJob,identity).cancel_requested=1
    release.set(); await task
    with sessions() as db:
        assert db.get(ResearchJob,identity).status=='CANCELLED'
        assert not list(db.scalars(select(ResearchTrial).where(ResearchTrial.job_id==identity)))
    identity,_=research_job(); called.clear(); release.clear()
    with sessions.begin() as db: db.get(SandboxLease,'benchmark').expires_at=0
    task=asyncio.create_task(ResearchRunner(sessions,controlled).run(identity)); await called.wait()
    with sessions.begin() as db: db.get(ResearchJob,identity).owner='another-owner'
    release.set(); await task
    with sessions() as db:
        assert db.get(ResearchJob,identity).status=='RUNNING' # stale owner cannot finish replacement job
        assert not list(db.scalars(select(ResearchTrial).where(ResearchTrial.job_id==identity)))

async def test_job_timeout(sessions,research_job):
    identity,_=research_job()
    with sessions.begin() as db: db.get(ResearchJob,identity).deadline=time.time()+.04
    async def slow(s,variant='original'): await asyncio.sleep(1)
    await ResearchRunner(sessions,slow).run(identity)
    with sessions() as db: assert db.get(ResearchJob,identity).status=='FAILED'

async def test_missing_adapter_not_finding(monkeypatch):
    import app.benchmarks.executor as module
    real=httpx.AsyncClient
    def handler(request):
        if request.url.path=='/health': return httpx.Response(200,json={'version':'test'})
        if request.method=='DELETE': return httpx.Response(200,json={})
        if request.url.path=='/checkout': return httpx.Response(200,json={'events':[]})
        return httpx.Response(503,json={'error':'observation unavailable'})
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(handler),**kwargs))
    result=await HTTPExecutor({r:'http://127.0.0.1:1' for r in ('gateway','order','payment','inventory')},'test')(Scenario(defect='payment_ack_loss'))
    assert result['classification']=='INCONCLUSIVE' and result['signature'] is None

async def test_repair_then_verifier_reports_unavailable(sessions,research_job,research_cluster,tmp_path,monkeypatch):
    monkeypatch.setenv('REPAIR_WORKSPACE_ROOT',str(tmp_path)); monkeypatch.delenv('REPAIR_AGENT_URL',raising=False)
    identity,project=research_job(); runner=ResearchRunner(sessions,HTTPExecutor(*research_cluster)); await runner.run(identity)
    # Repair tests use a measured witness, independent of whether a two-trial search finds it.
    measured=await HTTPExecutor(*research_cluster)(witness('payment_ack_loss'))
    assert measured['classification']=='APPLICATION_VIOLATION'
    with sessions.begin() as db:
        source=ResearchTrial(job_id=identity,project_id=project,**measured); db.add(source); db.flush()
    async def submit(kind,**kwargs):
        with sessions.begin() as db:
            db.get(SandboxLease,'benchmark').expires_at=0
            body=ResearchCreate(kind=kind,idempotency_key=kind,**kwargs)
            row=ResearchJob(project_id=project,idempotency_key=kind,kind=kind,input=body.model_dump(),deadline=time.time()+30); db.add(row); db.flush(); key=row.id
        await runner.run(key)
        with sessions() as db: return db.get(ResearchJob,key)
    repaired=await submit('REPAIR',source_trial_id=source.id)
    assert repaired.status=='COMPLETED'
    verified=await submit('VERIFY',candidate_id=repaired.result['candidate_id'])
    assert verified.status=='COMPLETED' and verified.result['outcome']=='INFRASTRUCTURE_ERROR'

def test_agent_auth_and_literal_patch_restrictions(monkeypatch):
    from app.repair.agent import app
    monkeypatch.setenv('REPAIR_AGENT_TOKEN','test-agent-token')
    client=TestClient(app)
    body={'candidate_id':'00000000-0000-4000-8000-000000000001','source':'import os','base_sha256':'a'*64,'scenario':witness('payment_ack_loss').model_dump()}
    assert client.post('/verify',json=body).status_code==401
    assert client.post('/verify',json=body,headers={'Authorization':'Bearer test-agent-token'}).status_code==422
    assert client.post('/verify',json={**body,'command':'sh'},headers={'Authorization':'Bearer test-agent-token'}).status_code==422

async def test_minimization_unknown_neighbors_do_not_prove_minimality():
    calls=0
    async def execute(s,variant='original'):
        nonlocal calls
        calls+=1
        return {'id':str(calls),'classification':'APPLICATION_VIOLATION' if s.actions and s.amount==100 else 'INCONCLUSIVE','signature':'same' if s.actions and s.amount==100 else None,'cost_seconds':.01}
    report=await minimize(witness('payment_ack_loss'),'same',execute,60,2)
    assert not report.local_minimality_tested

@pytest.mark.skipif(__import__('shutil').which('docker') is None,reason='Docker unavailable: generated candidate execution requires restricted verification container')
def test_generated_patch_inside_restricted_docker(tmp_path,monkeypatch):
    import subprocess
    from app.repair.agent import app
    monkeypatch.setenv('REPAIR_WORKSPACE_ROOT',str(tmp_path)); monkeypatch.setenv('REPAIR_AGENT_TOKEN','test-agent-token')
    subprocess.run(['docker','image','inspect','failurelab-verifier:phase3'],check=True,capture_output=True)
    patch,metadata=prepare('payment_ack_loss')
    body={'candidate_id':'00000000-0000-4000-8000-000000000001','source':metadata['source'],'base_sha256':metadata['base_sha256'],'scenario':witness('payment_ack_loss').model_dump()}
    response=TestClient(app).post('/verify',json=body,headers={'Authorization':'Bearer test-agent-token'})
    assert response.status_code==200 and response.json()['outcome']=='PATCH_PASSES_TESTED_SCENARIOS',response.text
    assert len(response.json()['cases'])==6

def test_real_research_worker_crash_and_recovery(sessions,research_job,research_cluster,tmp_path):
    import os,shutil,subprocess,sys,uuid
    import redis
    from celery import Celery
    from app.core.db import make_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.entities import SandboxLease
    from app.models.research import ResearchTrial
    binary=shutil.which('redis-server')
    broker=os.getenv('TEST_REDIS_URL')
    if not broker and not binary: pytest.skip('Real research recovery requires Redis; no eager fallback')
    from app.benchmarks.local import port
    root=Path(__file__).resolve().parents[2]; processes=[]; handles=[]
    if not broker:
        broker='redis://127.0.0.1:'+str(port())+'/0'
        log=open(tmp_path/'redis.log','w');handles.append(log)
        processes.append(subprocess.Popen([binary,'--bind','127.0.0.1','--port',broker.split(':')[-1].split('/')[0],'--save','','--appendonly','no'],stdout=log,stderr=log))
    connection=redis.Redis.from_url(broker); publisher=Celery('research-test',broker=broker); queue='research-'+uuid.uuid4().hex
    identity,project=research_job()
    with sessions.begin() as db:
        row=db.get(ResearchJob,identity); config=dict(row.input); config['search']={**config['search'],'budget':60};row.input=config
    urls,token=research_cluster
    env={**os.environ,'PYTHONPATH':str(root/'backend'),'DATABASE_URL':str(sessions.kw['bind'].url),'REDIS_URL':broker,'CELERY_QUEUE':queue,'CONTROL_TOKEN':token,**{'BENCH_'+r.upper()+'_URL':u for r,u in urls.items()}}
    def wait(predicate,seconds=35):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if predicate(): return
            time.sleep(.05)
        pytest.fail('Research worker recovery condition timed out; inspect '+str(tmp_path))
    def ping():
        try:return connection.ping()
        except redis.ConnectionError:return False
    def worker():
        log=open(tmp_path/('worker-'+str(len(handles))+'.log'),'w');handles.append(log)
        p=subprocess.Popen([sys.executable,'-m','celery','-A','app.workers.tasks.celery','worker','--pool=solo','--loglevel=INFO','--without-gossip','--without-mingle','--without-heartbeat','-Q',queue],cwd=root,env=env,stdout=log,stderr=log);processes.append(p);return p
    def has_trial():
        with sessions() as db:return db.scalar(select(ResearchTrial.id).where(ResearchTrial.job_id==identity)) is not None
    def recovered():
        with sessions() as db:return db.get(ResearchJob,identity).status=='FAILED'
    try:
        wait(ping); process=worker(); publisher.send_task('failurelab.research',args=[identity],queue=queue)
        wait(has_trial); process.kill();process.wait(timeout=5)
        with sessions.begin() as db: db.get(ResearchJob,identity).deadline=time.time()-1
        worker();publisher.send_task('failurelab.dispatch',queue=queue);wait(recovered)
        with sessions() as db:
            row=db.get(ResearchJob,identity); assert 'worker lost' in row.error and row.result=={}
            assert db.scalar(select(ResearchTrial.id).where(ResearchTrial.job_id==identity))
            assert db.get(SandboxLease,'benchmark').expires_at>time.time() # retained crash safety hold
    finally:
        publisher.close();connection.delete(queue);connection.close()
        for p in reversed(processes):
            if p.poll() is None:p.terminate()
        for p in reversed(processes):
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        for h in handles:h.close()

async def test_model_proposals_reject_unknown_evidence(monkeypatch):
    import app.providers.ollama as provider
    monkeypatch.delenv('OLLAMA_URL',raising=False)
    assert (await provider.propose(['known'],{}))['status']=='DISABLED'
    monkeypatch.setenv('OLLAMA_URL','http://127.0.0.1:11434');real=httpx.AsyncClient
    proposal={'proposals':[{'description':'A proposal','evidence_ids':['invented'],'policy_defect':'payment_ack_loss'}]}
    monkeypatch.setattr(provider.httpx,'AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'message':{'content':json.dumps(proposal)}})),**kwargs))
    assert (await provider.propose(['known'],{}))['status']=='UNAVAILABLE_OR_INVALID'

async def test_counterfactual_real_http_reference_control(research_cluster):
    execute=HTTPExecutor(*research_cluster)
    async def reference(s): return await execute(s,'reference')
    report=await compare('trusted-reference-control',witness('payment_ack_loss'),execute,reference)
    assert report.outcome=='PATCH_PASSES_TESTED_SCENARIOS'
    assert len(report.cases)==6 and all(c['candidate']['classification']=='NO_VIOLATION' for c in report.cases)
    assert report.cases[0]['original']['classification']=='APPLICATION_VIOLATION'
    assert all(c['gateway_cpu_overhead_seconds'] is not None for c in report.cases)
    # This exercises the comparator with shipped trusted recovery code; generated patches still require Docker.

def test_agent_uses_fixed_limits_and_immutable_image(tmp_path,monkeypatch):
    import app.repair.agent as agent
    monkeypatch.setenv('REPAIR_WORKSPACE_ROOT',str(tmp_path)); monkeypatch.setenv('REPAIR_AGENT_TOKEN','unit-agent-token')
    monkeypatch.setattr(agent.shutil,'which',lambda name:'/test/docker')
    patch,metadata=prepare('payment_ack_loss'); calls=[]; identity='00000000-0000-4000-8000-000000000001'
    digest='sha256:'+'a'*64
    class Process:
        returncode=0
        def __init__(self,output=b''):self.output=output
        async def communicate(self):return self.output,b''
        async def wait(self):return 0
    async def spawn(*command,**kwargs):
        calls.append(command)
        if command[1]=='image':return Process(digest.encode())
        if command[1]=='run':return Process(json.dumps({'outcome':'INCONCLUSIVE','candidate_id':identity,'reason':'Unit transport fixture; no container executed'}).encode())
        return Process()
    monkeypatch.setattr(agent.asyncio,'create_subprocess_exec',spawn)
    response=TestClient(agent.app).post('/verify',json={'candidate_id':identity,'source':metadata['source'],'base_sha256':metadata['base_sha256'],'scenario':witness('payment_ack_loss').model_dump()},headers={'Authorization':'Bearer unit-agent-token'})
    assert response.status_code==200 and response.json()['environment']['verification_image_id']==digest
    command=next(c for c in calls if c[1]=='run')
    assert command[-1]==digest and '--network' in command and command[command.index('--network')+1]=='none'
    for flag in ['--read-only','--cap-drop','--security-opt','--cpus','--memory','--pids-limit','--user','--tmpfs']: assert flag in command
    assert not any(arg=='/var/run/docker.sock' for arg in command)
    assert any(c[1:3]==('rm','--force') for c in calls)

async def test_real_multi_fault_reduction(research_cluster):
    execute=HTTPExecutor(*research_cluster)
    scenario=witness('payment_ack_loss');scenario.actions.append(Action(boundary='reserve',kind='latency',phase='before',delay_ms=10))
    original=await execute(scenario);assert original['classification']=='APPLICATION_VIOLATION'
    report=await minimize(scenario,original['signature'],execute,40,2)
    assert len(report.original.actions)==2 and len(report.reduced.actions)==1
    assert report.reduced.actions[0].boundary=='charge'
    assert any(a.boundary=='reserve' for a in report.removed_events)

async def test_publication_fence_closes_check_write_race(sessions,research_job):
    identity,_=research_job();checks=0
    async def measured(s,variant='original'):
        return {'id':'not-published','scenario':s.model_dump(),'variant':variant,'classification':'NO_VIOLATION','signature':None,'cost_seconds':.01,'evidence':{}}
    runner=ResearchRunner(sessions,measured); original_check=runner.check
    def raced(job_id,owner):
        nonlocal checks
        original_check(job_id,owner);checks+=1
        if checks==2:
            with sessions.begin() as db:db.get(ResearchJob,identity).owner='replacement-owner'
    runner.check=raced
    await runner.run(identity)
    with sessions() as db:
        assert not list(db.scalars(select(ResearchTrial).where(ResearchTrial.job_id==identity)))
        assert db.get(ResearchJob,identity).owner=='replacement-owner'
