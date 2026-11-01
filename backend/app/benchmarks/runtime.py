"""Managed HTTP benchmark services. No externally selectable destinations or commands.

Faults act at real request boundaries; after faults commit the transaction before
losing/delaying its acknowledgement. Receipts are durable and scoped to a UUID.
"""
import asyncio
import hmac
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Literal
import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import Field
from sqlalchemy import String, Integer, JSON, select, delete, func, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.exc import IntegrityError
from app.core.db import make_engine
from app.schemas.contracts import Contract
from app.schemas.research import Scenario
from app.benchmarks.policies import POLICIES

class Store(DeclarativeBase): pass
class Record(Store):
    __tablename__='benchmark_records'
    __table_args__=(UniqueConstraint('namespace','key'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    namespace: Mapped[str]=mapped_column(String(36),index=True)
    key: Mapped[str]=mapped_column(String(100))
    status: Mapped[str]=mapped_column(String(30))
    amount: Mapped[int]=mapped_column(Integer,default=0)
    quantity: Mapped[int]=mapped_column(Integer,default=0)
class Receipt(Store):
    __tablename__='benchmark_receipts'
    __table_args__=(UniqueConstraint('namespace','action','hit'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    namespace: Mapped[str]=mapped_column(String(36),index=True)
    action: Mapped[int]=mapped_column(Integer)
    hit: Mapped[int]=mapped_column(Integer)
    payload: Mapped[dict]=mapped_column(JSON)
class Operation(Contract):
    namespace: uuid.UUID
    scenario: Scenario
    variant: Literal['original','reference']='original'
    op: Literal['create','reserve','charge','finalize','cancel','refund','release']
    key: str=Field('business',pattern=r'^[a-zA-Z0-9_-]{1,60}$')
    elapsed_ms: int=Field(0,ge=0,le=10000)
class Checkout(Contract):
    namespace: uuid.UUID
    scenario: Scenario
    variant: Literal['original','reference']='original'

def origins():
    from app.research.config import service_origins
    return service_origins()

def create_app(role=None, database_url=None):
    role=role or os.getenv('BENCH_ROLE','gateway')
    if role not in ('gateway','order','payment','inventory'): raise ValueError('invalid benchmark role')
    engine=make_engine(database_url or os.getenv('BENCH_DATABASE_URL','sqlite:///benchmark-'+role+'.db'))
    if engine.dialect.name=='postgresql':
        from sqlalchemy import text
        with engine.begin() as db: db.execute(text('CREATE SCHEMA IF NOT EXISTS bench_'+role))
        engine=engine.execution_options(schema_translate_map={None:'bench_'+role})
    sessions=sessionmaker(engine,expire_on_commit=False)
    @asynccontextmanager
    async def lifespan(app):
        Store.metadata.create_all(engine)
        yield
        engine.dispose()
    from app.core.limits import BodyLimit
    app=FastAPI(title='FailureLab managed benchmark '+role,lifespan=lifespan)
    app.add_middleware(BodyLimit)
    token=os.getenv('CONTROL_TOKEN','local-control-token')
    async def auth(x_control_token: str=Header(default='')):
        if not hmac.compare_digest(x_control_token,token): raise HTTPException(401,'invalid sandbox token')
    from fastapi import Depends
    app.router.dependencies.append(Depends(auth))
    lock=asyncio.Lock() # one gateway trial at a time; request faults never escape a namespace
    @app.get('/health')
    def health(): return {'role':role,'version':os.getenv('BUILD_VERSION','development'),'policy_sha256':__import__('hashlib').sha256(repr(POLICIES).encode()).hexdigest(),'runtime_sha256':__import__('hashlib').sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest(),'python':__import__('sys').version.split()[0]}
    @app.delete('/state/{namespace}')
    def reset(namespace:uuid.UUID):
        with sessions.begin() as db:
            db.execute(delete(Record).where(Record.namespace==str(namespace)))
            db.execute(delete(Receipt).where(Receipt.namespace==str(namespace)))
        return {'removed':str(namespace)}
    @app.get('/state/{namespace}')
    def state(namespace:uuid.UUID):
        with sessions() as db:
            rows=list(db.scalars(select(Record).where(Record.namespace==str(namespace)).order_by(Record.id)))
            receipts=list(db.scalars(select(Receipt).where(Receipt.namespace==str(namespace)).order_by(Receipt.action,Receipt.hit)))
        if role=='order':
            current=rows[0] if rows else None
            snapshot={'status':current.status if current else 'absent','amount':current.amount if current else 0,'quantity':current.quantity if current else 0}
        elif role=='payment': snapshot={'status':'charged' if sum(r.amount for r in rows)>0 else 'absent','amount':sum(r.amount for r in rows),'quantity':len(rows)}
        else: snapshot={'status':'reserved' if sum(r.quantity for r in rows)>0 else 'absent','amount':0,'quantity':sum(r.quantity for r in rows)}
        return {'state':snapshot,'records':[{'key':r.key,'status':r.status,'amount':r.amount,'quantity':r.quantity} for r in rows], 'receipts':[r.payload for r in receipts]}
    async def inject(body,phase):
        for index,action in enumerate(body.scenario.actions):
            if action.boundary!=body.op or action.phase!=phase or body.elapsed_ms<action.at_ms: continue
            with sessions.begin() as db:
                count=db.scalar(select(func.count()).select_from(Receipt).where(Receipt.namespace==str(body.namespace),Receipt.action==index))
                if count>=action.max_hits: continue
                db.add(Receipt(namespace=str(body.namespace),action=index,hit=count,payload={'action_index':index,'boundary':body.op,'phase':phase,'kind':action.kind,'applied_at':time.time(),'delay_ms':action.delay_ms,'effective_delay_ms':500 if action.kind=='timeout' else (action.delay_ms if action.kind=='latency' else 0)}))
            if action.kind=='http_503': raise HTTPException(503,'controlled sandbox response')
            await asyncio.sleep((500 if action.kind=='timeout' else action.delay_ms)/1000)
    @app.post('/operate')
    async def operate(body:Operation):
        allowed={'order':{'create','finalize','cancel'},'payment':{'charge','refund'},'inventory':{'reserve','release'},'gateway':set()}
        if body.op not in allowed[role]: raise HTTPException(422,'operation does not belong to service')
        await inject(body,'before')
        fixed=body.variant=='reference' or POLICIES[body.scenario.defect]
        namespace=str(body.namespace)
        if body.op in ('charge','reserve'):
            safe=not ((body.op=='reserve' and body.scenario.defect=='inventory_drift') or (body.op=='charge' and body.scenario.defect=='concurrent_retry')) or fixed
            key=body.key
            with sessions() as db:
                existing=db.scalar(select(Record).where(Record.namespace==namespace,Record.key==key))
            if existing is None or not safe:
                # Actual check/await/write race in the flawed concurrent payment path.
                if body.scenario.defect=='concurrent_retry' and body.op=='charge' and not fixed: await asyncio.sleep(.035)
                if not safe: key=key+'-'+uuid.uuid4().hex[:12]
                try:
                    with sessions.begin() as db:
                        db.add(Record(namespace=namespace,key=key,status='charged' if body.op=='charge' else 'reserved',amount=body.scenario.amount if body.op=='charge' else 0,quantity=body.scenario.quantity if body.op=='reserve' else 0))
                except IntegrityError: pass # atomic unique business key handles simultaneous retries
        else:
            with sessions.begin() as db:
                row=db.scalar(select(Record).where(Record.namespace==namespace,Record.key=='business'))
                if body.op=='create' and row is None:
                    db.add(Record(namespace=namespace,key='business',status='pending',amount=body.scenario.amount,quantity=body.scenario.quantity))
                elif body.op in ('finalize','cancel'):
                    if row is None: raise HTTPException(409,'order absent')
                    row.status='finalized' if body.op=='finalize' else 'cancelled'
                elif body.op in ('refund','release'):
                    for row in db.scalars(select(Record).where(Record.namespace==namespace)):
                        row.amount=0; row.quantity=0; row.status='compensated'
        await inject(body,'after')
        return {'status':'acknowledged','operation':body.op}
    @app.post('/checkout')
    async def checkout(body:Checkout):
        if role!='gateway': raise HTTPException(422,'gateway operation only')
        async with lock:
            start=time.monotonic(); cpu=time.process_time(); events=[]
            fixed=body.variant=='reference' or POLICIES[body.scenario.defect]
            def finish(outcome):
                return {'events':events,'outcome':outcome,'wall_seconds':time.monotonic()-start,'gateway_cpu_seconds':time.process_time()-cpu}
            urls=origins()
            async with httpx.AsyncClient(trust_env=False,headers={'X-Control-Token':token},timeout=.09) as client:
                async def call(service,op,key='business',attempt=0):
                    data=Operation(**body.model_dump(),op=op,key=key,elapsed_ms=int((time.monotonic()-start)*1000)).model_dump(mode='json')
                    try:
                        response=await client.post(urls[service]+'/operate',json=data); response.raise_for_status()
                        events.append({'service':service,'operation':op,'attempt':attempt,'status':response.status_code,'at_ms':int((time.monotonic()-start)*1000)})
                        return True
                    except httpx.HTTPError as exc:
                        events.append({'service':service,'operation':op,'attempt':attempt,'error':type(exc).__name__,'at_ms':int((time.monotonic()-start)*1000)})
                        return False
                if not await call('order','create'): return finish('create_failed')
                reserved=await call('inventory','reserve')
                if not reserved and body.scenario.defect=='inventory_drift': reserved=await call('inventory','reserve',attempt=1)
                if not reserved: return finish('reserve_failed')
                if body.scenario.concurrency==2:
                    paid=all(await asyncio.gather(call('payment','charge'),call('payment','charge',attempt=1)))
                else: paid=await call('payment','charge')
                if not paid:
                    if body.scenario.defect=='unsafe_retry': paid=await call('payment','charge',key='business' if fixed else 'retry-new-key',attempt=1)
                    elif fixed: paid=await call('payment','charge',attempt=1)
                if not paid: return finish('payment_acknowledgement_failed')
                finalized=await call('order','finalize')
                if not finalized and fixed and body.scenario.defect!='failed_compensation': finalized=await call('order','finalize',attempt=1)
                if not finalized and body.scenario.defect=='failed_compensation':
                    await call('order','cancel')
                    refunded=await call('payment','refund')
                    if not refunded and fixed: await call('payment','refund',attempt=1)
                    await call('inventory','release')
                return finish('finalized' if finalized else 'unresolved')
    return app
