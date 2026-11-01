import time
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.core.security import Policy,Principal,rate_limit
from app.models.audit import AuditEvent
from app.models.entities import Project

@pytest.fixture
def security_client(sessions,monkeypatch):
    from app.main import app
    from app.core.db import get_db
    import app.core.security as security
    def database():
        with sessions() as db:yield db
    app.dependency_overrides[get_db]=database
    monkeypatch.setattr(security,'rate_limit',lambda *args,**kwargs:None)
    monkeypatch.setenv('APP_MODE','hosted')
    tokens={r:(r+'-test-')+'x'*40 for r in ('viewer','operator','admin')}
    for role,token in tokens.items():monkeypatch.setenv('AUTH_'+role.upper()+'_TOKEN',token)
    yield TestClient(app),tokens
    app.dependency_overrides.clear()

def test_role_boundaries_and_audit(sessions,security_client):
    client,tokens=security_client
    def headers(role):return {'Authorization':'Bearer '+tokens[role]}
    assert client.get('/api/v1/projects').status_code==401
    assert client.get('/api/v1/projects',headers=headers('viewer')).status_code==200
    assert client.get('/api/v1/session',headers=headers('viewer')).json()['can_execute'] is False
    assert client.post('/api/v1/projects',json={'name':'forbidden'},headers=headers('viewer')).status_code==403
    assert client.post('/api/v1/projects',json={'name':'forbidden'},headers=headers('operator')).status_code==403
    created=client.post('/api/v1/projects',json={'name':'authorized'},headers=headers('admin'))
    assert created.status_code==201 and created.headers['x-request-id']
    duplicate=client.post('/api/v1/projects',json={'name':'authorized'},headers=headers('admin'));assert duplicate.status_code==409
    with sessions() as db:assert db.scalar(select(AuditEvent).where(AuditEvent.request_id==duplicate.headers['x-request-id'])).status==409
    assert client.get('/api/v1/admin/audit',headers=headers('viewer')).status_code==403
    response=client.get('/api/v1/admin/audit',headers=headers('admin'));assert response.status_code==200
    assert all(token not in response.text for token in tokens.values())
    with sessions() as db:
        audit=db.scalar(select(AuditEvent).where(AuditEvent.request_id==created.headers['x-request-id']))
        assert audit.status==201 and audit.role=='admin' and audit.route=='/api/v1/projects'
        assert db.scalar(select(Project).where(Project.name=='forbidden')) is None

def test_read_only_blocks_even_admin_and_legacy_disabled(security_client,monkeypatch):
    client,tokens=security_client;monkeypatch.setenv('APP_MODE','read_only')
    assert client.post('/api/v1/projects',json={'name':'never'},headers={'Authorization':'Bearer '+tokens['admin']}).status_code==403
    assert client.get('/api/v1/projects',headers={'Authorization':'Bearer local-development-token'}).status_code==401
    assert client.get('/api/v1/session',headers={'Authorization':'Bearer '+tokens['admin']}).json()['read_only']

def test_execution_role_policy():
    policy=Policy('hosted',{},30);operator=Principal('unit','operator');viewer=Principal('unit','viewer')
    for path in ['/api/v1/experiments/x/runs','/api/v1/runs/x/cancel','/api/v1/research/projects/x/jobs','/api/v1/research/jobs/x/cancel','/api/v1/projects/x/experiments']:
        policy.allow(operator,'POST',path)
        with pytest.raises(Exception) as exc:policy.allow(viewer,'POST',path)
        assert exc.value.status_code==403
    with pytest.raises(Exception):policy.allow(operator,'POST','/api/v1/projects/x/services')

def test_hosted_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv('APP_MODE','hosted')
    for r in ('VIEWER','OPERATOR','ADMIN'):monkeypatch.delenv('AUTH_'+r+'_TOKEN',raising=False)
    with pytest.raises(ValueError):Policy.load()
    monkeypatch.setenv('AUTH_VIEWER_TOKEN','short')
    with pytest.raises(ValueError):Policy.load()
    monkeypatch.setenv('AUTH_VIEWER_TOKEN','v'*40);monkeypatch.setenv('AUTH_ADMIN_TOKEN','v'*40)
    with pytest.raises(ValueError):Policy.load()

def test_invalid_input_is_not_reflected(security_client):
    client,tokens=security_client
    response=client.post('/api/v1/projects',json={'name':'okay','secret':'do-not-reflect-this-value'},headers={'Authorization':'Bearer '+tokens['admin']})
    assert response.status_code==422 and 'do-not-reflect' not in response.text

def test_rate_limiter_atomic_contract_and_failure():
    from fastapi import HTTPException
    import redis
    class Counter:
        def __init__(self):self.n=0;self.args=[]
        def eval(self,*args):self.args.append(args);self.n+=1;return self.n
    counter=Counter();rate_limit('hashed','mutation',1,client=counter,now=100)
    with pytest.raises(HTTPException) as exc:rate_limit('hashed','mutation',1,client=counter,now=100)
    assert exc.value.status_code==429 and 'EXPIRE' in counter.args[0][0]
    class Broken:
        def eval(self,*args):raise redis.ConnectionError('not logged')
    with pytest.raises(HTTPException) as exc:rate_limit('hashed','mutation',1,client=Broken())
    assert exc.value.status_code==503

def test_rate_limits_share_actual_redis_counter(tmp_path):
    import os,shutil,subprocess,time,uuid
    import redis
    from app.benchmarks.local import port
    url=os.getenv('TEST_REDIS_URL');process=None
    log=open(tmp_path/'security-redis.log','w')
    if not url:
        binary=shutil.which('redis-server')
        if not binary:pytest.skip('Redis unavailable; distributed limit integration not executed')
        number=port();url=f'redis://127.0.0.1:{number}/15'
        process=subprocess.Popen([binary,'--bind','127.0.0.1','--port',str(number),'--save','','--appendonly','no'],stdout=log,stderr=log)
    first=redis.Redis.from_url(url);second=redis.Redis.from_url(url);identity=uuid.uuid4().hex
    try:
        deadline=time.monotonic()+10
        while True:
            try:
                if first.ping():break
            except redis.ConnectionError:pass
            if time.monotonic()>deadline:pytest.fail('Owned Redis did not start')
            time.sleep(.05)
        rate_limit(identity,'security-test',2,client=first,now=120)
        rate_limit(identity,'security-test',2,client=second,now=120)
        with pytest.raises(Exception) as exc:rate_limit(identity,'security-test',2,client=first,now=120)
        assert exc.value.status_code==429
        key='failurelab:limit:security-test:'+identity+':2';assert 0<first.ttl(key)<=65
        first.delete(key)
    finally:
        first.close();second.close()
        if process:process.terminate();process.wait(timeout=5)
        log.close()

async def test_body_deadline_and_fragmentation_are_bounded():
    import asyncio
    from app.core.limits import BodyLimit
    sent=[];called=[]
    async def downstream(*args):called.append(True)
    async def send(message):sent.append(message)
    async def slow():await asyncio.sleep(1)
    await BodyLimit(downstream,timeout=.01)({'type':'http'},slow,send)
    assert sent[0]['status']==408 and not called
    sent.clear()
    async def fragmented():return {'type':'http.request','body':b'x','more_body':True}
    await BodyLimit(downstream,max_chunks=2)({'type':'http'},fragmented,send)
    assert sent[0]['status']==413 and not called
