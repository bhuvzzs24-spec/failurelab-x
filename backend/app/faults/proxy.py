"""Restricted HTTP/1 sandbox proxy. Data plane is raw TCP to support real resets.
Control plane runs separately, authenticated; upstream is fixed by operator config.
"""
import asyncio
import os
import time
import hmac
from contextlib import asynccontextmanager
import httpx
import uvicorn
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import Field
from app.schemas.contracts import Contract, Fault
from app.core.config import settings

class Lease(Contract):
    execution_id: str = Field(pattern=r"^[a-zA-Z0-9-]{1,64}$")
    fault: Fault

class ProxyState:
    def __init__(self): self.lease = None; self.expires = 0.0; self.changed = asyncio.Event(); self.lock = asyncio.Lock()
    def current(self):
        if time.monotonic() >= self.expires: self.lease = None
        return self.lease

state = ProxyState()
async def auth(x_control_token: str = Header(default="")):
    if not hmac.compare_digest(x_control_token,settings().control_token): raise HTTPException(401,"invalid control token")

app = FastAPI(title="FailureLab restricted fault control")
from app.telemetry.logging import configure, instrument
configure(); instrument(app)
@app.get("/health")
def health(): return {"status":"ok", "version":settings().version}
@app.put("/lease", dependencies=[Depends(auth)])
async def activate(body: Lease):
    async with state.lock:
        current = state.current()
        if current and current.execution_id != body.execution_id: raise HTTPException(409,"sandbox already leased")
        if body.fault.kind == "worker_interrupt":
            async with httpx.AsyncClient(trust_env=False) as client:
                response = await client.put(settings().payment+"/control/pause",json={"execution_id":body.execution_id,"seconds":body.fault.duration_seconds},headers={"X-Control-Token":settings().control_token})
                response.raise_for_status()
        state.changed.set(); state.changed = asyncio.Event()
        state.lease = body; state.expires = time.monotonic()+body.fault.duration_seconds
        return {"execution_id":body.execution_id,"expires_in":body.fault.duration_seconds}
@app.delete("/lease/{execution_id}", dependencies=[Depends(auth)])
async def cleanup(execution_id: str):
    async with state.lock:
        current=state.current()
        if current and current.execution_id != execution_id: raise HTTPException(409,"lease owned by another execution")
        async with httpx.AsyncClient(trust_env=False) as client:
            response=await client.delete(settings().payment+"/control/pause/"+execution_id,headers={"X-Control-Token":settings().control_token})
            response.raise_for_status()
        state.changed.set()
        state.lease = None; state.expires=0
        return {"restored":True}
@app.get("/lease", dependencies=[Depends(auth)])
async def lease():
    current=state.current()
    return {"active":current.model_dump() if current else None,"remaining_seconds":max(0,state.expires-time.monotonic())}

async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        head=await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"),2)
        if len(head)>8192: raise ValueError("headers too large")
        lines=head.decode("ascii").split("\r\n")
        method,path,_=lines[0].split(" ")
        headers=dict(line.split(":",1) for line in lines[1:] if line)
        headers={k.lower():v.strip() for k,v in headers.items()}
        if method != "POST" or path != "/charge" or "transfer-encoding" in headers:
            await send(writer,403,b'{"detail":"boundary not allowed"}'); return
        size=int(headers.get("content-length","0"))
        if not 0<size<=4096: raise ValueError("invalid body size")
        body=await asyncio.wait_for(reader.readexactly(size),2)
        lease=state.current(); fault=lease.fault if lease else None
        execution_id=headers.get("x-execution-id","")
        # Fault scope includes the execution ID, not all traffic through the proxy.
        if lease and execution_id != lease.execution_id: fault=None
        if fault and fault.phase == "before":
            if await apply(fault,writer,lease): return
        async with httpx.AsyncClient(timeout=12,trust_env=False) as client:
            response=await client.post(settings().payment+"/charge",content=body,headers={
                "Content-Type":"application/json", "X-Execution-ID":execution_id,
                "traceparent":headers.get("traceparent","")})
        if fault and fault.phase == "after":
            if await apply(fault,writer,lease): return
        await send(writer,response.status_code,response.content)
    except (asyncio.IncompleteReadError,ConnectionError): pass
    except Exception:
        if not writer.is_closing():
            try: await send(writer,502,b'{"detail":"proxy upstream failure"}')
            except ConnectionError: pass
    finally:
        writer.close()
        try: await writer.wait_closed()
        except ConnectionError: pass

async def apply(fault,writer,lease):
    if state.current() is not lease: return False
    remaining=max(0,state.expires-time.monotonic())
    async def delay(seconds):
        try:
            await asyncio.wait_for(state.changed.wait(),timeout=min(seconds,remaining))
            return False
        except asyncio.TimeoutError: return True
    if fault.kind == "latency": await delay(fault.delay_seconds)
    elif fault.kind in {"timeout","unavailable"}:
        if not await delay(fault.duration_seconds): return False
        await send(writer,504,b'{"detail":"injected timeout"}'); return True
    elif fault.kind == "http_503":
        await send(writer,503,b'{"detail":"injected unavailable"}'); return True
    elif fault.kind == "reset":
        # SO_LINGER(1,0) closes TCP with RST rather than an HTTP response.
        import socket,struct
        sock=writer.get_extra_info("socket")
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack("ii",1,0))
        writer.transport.abort(); return True
    return False

async def send(writer,status,body):
    writer.write(f"HTTP/1.1 {status} Result\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode()+body)
    await writer.drain()

async def main():
    server=await asyncio.start_server(handle,os.getenv("BIND_HOST","0.0.0.0"),int(os.getenv("DATA_PORT","8000")),limit=8192)
    config=uvicorn.Config(app,host=os.getenv("BIND_HOST","0.0.0.0"),port=int(os.getenv("CONTROL_PORT","8001")),log_config=None)
    async with server: await uvicorn.Server(config).serve()
if __name__ == "__main__": asyncio.run(main())
