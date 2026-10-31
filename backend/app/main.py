import hmac
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.db import engine
from app.api.routes import router
from app.schemas.contracts import ErrorResponse

async def auth(authorization: str=Header(default="")):
    if not hmac.compare_digest(authorization,"Bearer "+settings().api_token): raise HTTPException(401,"invalid API token")

app=FastAPI(title="FailureLab X",version="0.1.0",responses={401:{"model":ErrorResponse},422:{"model":ErrorResponse},409:{"model":ErrorResponse},404:{"model":ErrorResponse}})
from app.telemetry.logging import configure, instrument
configure(); instrument(app)
from app.core.limits import BodyLimit
app.add_middleware(BodyLimit)
app.include_router(router,dependencies=[Depends(auth)])
@app.exception_handler(HTTPException)
async def http_error(request,exc):
    return JSONResponse(status_code=exc.status_code,content={"error":{"code":str(exc.status_code),"message":str(exc.detail)}})
@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    return JSONResponse(status_code=422,content={"error":{"code":"validation_error","message":str(exc)[:1000]}})
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
        with engine.connect() as connection: connection.execute(text("SELECT id FROM sandbox_leases LIMIT 1"))
        import redis
        redis.Redis.from_url(settings().broker_url,socket_connect_timeout=1,socket_timeout=1).ping()
        return {"status":"ready","database":True,"broker":True}
    except Exception:
        raise HTTPException(503,"database migration or broker unavailable")
