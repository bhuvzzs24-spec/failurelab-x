import os
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import Policy, RequestContext, authenticate, complete_audit
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.db import engine
from app.api.routes import router
from app.schemas.contracts import ErrorResponse

async def auth(request:Request,authorization: str=Header(default=""),db:Session=Depends(get_db)):
    await run_in_threadpool(authenticate,request,authorization,db)
    status=500
    try:
        yield request.state.principal
    except Exception as exc:
        status=409 if isinstance(exc,IntegrityError) else 422 if isinstance(exc,RequestValidationError) else getattr(exc,'status_code',500)
        raise
    finally:
        identity=getattr(request.state,'audit_id',None)
        if identity:
            try:
                if not db.is_active: db.rollback()
                await run_in_threadpool(complete_audit,db,identity,getattr(request.state,'response_status',status))
            except Exception:
                db.rollback()
                import logging
                logging.getLogger('failurelab').critical('Audit intent could not be finalized',extra={'request_id':request.state.request_id})

@asynccontextmanager
async def lifespan(app):
    Policy.load() # invalid hosted secrets fail startup, before accepting traffic
    yield

app=FastAPI(title="FailureLab X",version="0.1.0",lifespan=lifespan,docs_url='/docs' if os.getenv('APP_MODE','local')=='local' else None,redoc_url=None,openapi_url='/openapi.json' if os.getenv('APP_MODE','local')=='local' else None,responses={401:{"model":ErrorResponse},422:{"model":ErrorResponse},409:{"model":ErrorResponse},404:{"model":ErrorResponse}})
from app.telemetry.logging import configure, instrument
configure(); instrument(app)
from app.core.limits import BodyLimit
app.add_middleware(BodyLimit)
app.add_middleware(RequestContext)
app.include_router(router,dependencies=[Depends(auth)])
from app.api.overview import router as overview_router
app.include_router(overview_router,dependencies=[Depends(auth)])
@app.exception_handler(HTTPException)
async def http_error(request,exc):
    return JSONResponse(status_code=exc.status_code,headers=exc.headers,content={"error":{"code":str(exc.status_code),"message":str(exc.detail)}})
@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    return JSONResponse(status_code=422,content={"error":{"code":"validation_error","message":"request validation failed"}})
@app.exception_handler(IntegrityError)
async def integrity_error(request,exc):
    return JSONResponse(status_code=409,content={"error":{"code":"conflict","message":"constraint conflict"}})
@app.exception_handler(Exception)
async def unexpected_error(request,exc):
    import logging
    logging.getLogger("failurelab").exception("unhandled request failure")
    return JSONResponse(status_code=500,content={"error":{"code":"internal_error","message":"internal server error"}})

@app.get("/health")
def health(): return {"status":"ok","version":settings().version}
@app.get("/ready")
def ready():
    try:
        with engine.connect() as connection:
            version=connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if version!='0003': raise RuntimeError('database schema is not current')
            connection.execute(text("SELECT id FROM audit_events LIMIT 1"))
        import redis
        redis.Redis.from_url(settings().broker_url,socket_connect_timeout=1,socket_timeout=1).ping()
        return {"status":"ready","database":True,"broker":True}
    except Exception:
        raise HTTPException(503,"database migration or broker unavailable")

from app.api.research import router as research_router
app.include_router(research_router,dependencies=[Depends(auth)])

from app.api.security import router as security_router
app.include_router(security_router,dependencies=[Depends(auth)])
