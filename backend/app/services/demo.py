"""Same small image, separate role processes and persistent tables.
Payment processing is a background worker with a restricted TTL pause control.
"""
import asyncio
import hmac
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import Field
from sqlalchemy import String, Integer, select, delete, update
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker
from sqlalchemy.exc import IntegrityError
import httpx
from app.core.db import Base, make_engine
from app.core.config import settings
from app.schemas.contracts import Contract

class Transaction(Base):
    __tablename__="demo_transactions"
    role: Mapped[str] = mapped_column(String(20),primary_key=True)
    key: Mapped[str] = mapped_column(String(100),primary_key=True)
    status: Mapped[str] = mapped_column(String(30))
    amount: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)

class Stock(Base):
    __tablename__="demo_stock"
    sku: Mapped[str] = mapped_column(String(40),primary_key=True)
    available: Mapped[int] = mapped_column(Integer)

class Input(Contract):
    key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    amount: int = Field(ge=1,le=10000)
    quantity: int = Field(ge=1,le=10)
class Pause(Contract):
    execution_id: str = Field(pattern=r"^[a-zA-Z0-9-]{1,64}$")
    seconds: float = Field(ge=0,le=30)

async def control(x_control_token: str=Header(default="")):
    if not hmac.compare_digest(x_control_token,settings().control_token): raise HTTPException(401,"invalid control token")

def create_app(role: str | None = None, database_url: str | None = None):
    role=role or os.getenv("DEMO_ROLE","gateway")
    engine=make_engine(database_url or os.getenv("DEMO_DATABASE_URL", "sqlite:///demo.db"))
    sessions=sessionmaker(engine,expire_on_commit=False)
    pause={"until":0.0,"owner":None}
    async def payment_worker():
        while True:
            if time.monotonic()>=pause["until"]:
                with sessions.begin() as db:
                    db.execute(update(Transaction).where(Transaction.role=="payment",Transaction.status=="queued").values(status="charged"))
            await asyncio.sleep(.02)
    @asynccontextmanager
    async def lifespan(app):
        # Demo owns its own schema; platform schema uses Alembic.
        Transaction.__table__.create(engine,checkfirst=True)
        if role=="inventory":
            Stock.__table__.create(engine,checkfirst=True)
            with sessions.begin() as db:
                if not db.get(Stock,"demo-sku"): db.add(Stock(sku="demo-sku",available=100))
        task=asyncio.create_task(payment_worker()) if role=="payment" else None
        yield
        if task:
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass
        engine.dispose()
    from app.core.limits import BodyLimit
    app=FastAPI(title="FailureLab demo "+role,lifespan=lifespan)
    app.add_middleware(BodyLimit)
    from app.telemetry.logging import configure, instrument
    configure(); instrument(app)
    app.state.sessions=sessions
    @app.get("/health")
    def health(): return {"status":"ok","role":role,"version":settings().version,"payments":"test-only"}
    def write(body: Input,status: str):
        try:
            with sessions.begin() as db:
                row=db.get(Transaction,(role,body.key))
                if row:
                    if row.amount!=body.amount or row.quantity!=body.quantity: raise HTTPException(409,"idempotency key payload mismatch")
                    return {"status":row.status}
                db.add(Transaction(role=role,key=body.key,status=status,amount=body.amount,quantity=body.quantity))
            return {"status":status}
        except IntegrityError:
            return write(body,status)  # competing identical insert; re-read committed row
    @app.get("/state/{key}",dependencies=[Depends(control)])
    def state(key: str):
        with sessions() as db:
            row=db.get(Transaction,(role,key))
            return {"status":row.status,"amount":row.amount,"quantity":row.quantity} if row else {"status":"absent","amount":0,"quantity":0}
    @app.delete("/state",dependencies=[Depends(control)])
    def reset():
        with sessions.begin() as db:
            db.execute(delete(Transaction).where(Transaction.role==role))
            if role=="inventory": db.execute(update(Stock).where(Stock.sku=="demo-sku").values(available=100))
        return {"reset":role}
    @app.put("/control/pause",dependencies=[Depends(control)])
    async def stop(body: Pause):
        if role!="payment": raise HTTPException(400,"payment role only")
        if pause["until"]>time.monotonic() and pause["owner"]!=body.execution_id: raise HTTPException(409,"worker already leased")
        pause.update(until=time.monotonic()+body.seconds,owner=body.execution_id)
        return {"paused_seconds":body.seconds}
    @app.delete("/control/pause/{execution_id}",dependencies=[Depends(control)])
    async def resume(execution_id: str):
        if pause["until"]>time.monotonic() and pause["owner"]!=execution_id: raise HTTPException(409,"different lease owner")
        pause.update(until=0,owner=None); return {"resumed":True}
    if role=="order":
        @app.post("/orders",dependencies=[Depends(control)])
        def order(body: Input): return write(body,"pending")
        @app.post("/orders/{key}/finalize",dependencies=[Depends(control)])
        def finalize(key: str):
            with sessions.begin() as db:
                row=db.get(Transaction,(role,key))
                if not row: raise HTTPException(404,"order missing")
                row.status="finalized"
            return {"status":"finalized"}
    elif role=="inventory":
        @app.post("/reserve",dependencies=[Depends(control)])
        def reserve(body: Input):
            try:
                with sessions.begin() as db:
                    row=db.get(Transaction,(role,body.key))
                    if row:
                        if row.amount!=body.amount or row.quantity!=body.quantity: raise HTTPException(409,"idempotency key payload mismatch")
                        return {"status":row.status}
                    changed=db.execute(update(Stock).where(Stock.sku=="demo-sku",Stock.available>=body.quantity).values(available=Stock.available-body.quantity)).rowcount
                    if not changed: raise HTTPException(409,"insufficient stock")
                    db.add(Transaction(role=role,key=body.key,status="reserved",amount=body.amount,quantity=body.quantity))
                return {"status":"reserved"}
            except IntegrityError: return reserve(body)
        @app.get("/stock",dependencies=[Depends(control)])
        def stock():
            with sessions() as db: return {"sku":"demo-sku","available":db.get(Stock,"demo-sku").available}
    elif role=="payment":
        @app.post("/charge")
        async def charge(body: Input):
            write(body,"queued")
            # The persistent queued job survives a payment process restart.
            deadline=time.monotonic()+11
            while time.monotonic()<deadline:
                with sessions() as db:
                    row=db.get(Transaction,(role,body.key))
                    if row and row.status=="charged": return {"status":"charged","test_only":True}
                await asyncio.sleep(.02)
            raise HTTPException(504,"test payment worker paused")
    elif role=="gateway":
        @app.post("/checkout",dependencies=[Depends(control)])
        async def checkout(body: Input,x_execution_id: str=Header(default=""),traceparent: str=Header(default="")):
            headers={"X-Control-Token":settings().control_token,"X-Execution-ID":x_execution_id,"traceparent":traceparent}
            from opentelemetry.propagate import inject
            inject(headers)
            async with httpx.AsyncClient(timeout=3,trust_env=False,headers=headers) as client:
                response=await client.post(settings().order+"/orders",json=body.model_dump()); response.raise_for_status()
                response=await client.post(settings().inventory+"/reserve",json=body.model_dump()); response.raise_for_status()
                try:
                    response=await client.post(settings().proxy+"/charge",json=body.model_dump(),timeout=.5)
                    response.raise_for_status()
                except httpx.HTTPError:
                    # DELIBERATE BUG: no durable reconciliation or compensating transaction.
                    # Payment may already have committed while the response was lost.
                    raise HTTPException(504,"payment outcome unknown; order left pending")
                response=await client.post(settings().order+"/orders/"+body.key+"/finalize"); response.raise_for_status()
                return {"key":body.key,"status":"finalized"}
    else: raise ValueError("unknown demo role")
    return app
