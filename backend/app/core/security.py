"""Explicit local/hosted/read-only boundary. No public browser control credential.

Static role tokens are service/operator principals, not a user account system.
Hosted operators additionally need an identity-aware private ingress.
"""
import hashlib
import hmac
import os
import re
import time
import uuid
from dataclasses import dataclass
from typing import Literal
from fastapi import HTTPException, Request
from sqlalchemy import update
from app.core.config import settings
from app.models.audit import AuditEvent

Role=Literal['viewer','operator','admin']
@dataclass(frozen=True)
class Principal:
    actor_id: str
    role: Role
@dataclass(frozen=True)
class Policy:
    mode: str
    tokens: dict[str,str]
    mutations_per_minute: int
    @classmethod
    def load(cls):
        mode=os.getenv('APP_MODE','local')
        if mode not in ('local','hosted','read_only'): raise ValueError('APP_MODE must be local, hosted or read_only')
        tokens={role:os.getenv('AUTH_'+role.upper()+'_TOKEN','') for role in ('viewer','operator','admin')}
        tokens={role:token for role,token in tokens.items() if token}
        if mode!='local':
            if not tokens or 'viewer' not in tokens: raise ValueError('Hosted modes require AUTH_VIEWER_TOKEN')
            if any(len(t)<32 or t in (settings().api_token,settings().control_token) for t in tokens.values()): raise ValueError('Hosted role tokens must be distinct, at least 32 characters, and separate from legacy/control tokens')
        if any(t in (settings().api_token,settings().control_token) for t in tokens.values()): raise ValueError('Role tokens must not reuse legacy or fault-control secrets')
        if len(set(tokens.values()))!=len(tokens): raise ValueError('Role tokens must be unique')
        limit=int(os.getenv('MUTATIONS_PER_MINUTE','30'))
        if not 1<=limit<=300: raise ValueError('MUTATIONS_PER_MINUTE must be 1..300')
        return cls(mode,tokens,limit)
    def principal(self,authorization):
        if not authorization.startswith('Bearer '): raise HTTPException(401,'invalid API token')
        token=authorization[7:]; role=None
        for candidate,value in self.tokens.items():
            if hmac.compare_digest(token.encode(),value.encode()): role=candidate
        if self.mode=='local' and hmac.compare_digest(token.encode(),settings().api_token.encode()): role='admin'
        if role is None: raise HTTPException(401,'invalid API token')
        return Principal(hashlib.sha256(token.encode()).hexdigest(),role)
    def allow(self,principal,method,path):
        if path.startswith('/api/v1/admin/') and principal.role!='admin': raise HTTPException(403,'administrator role required')
        if method in ('GET','HEAD','OPTIONS'): return
        if self.mode=='read_only': raise HTTPException(403,'read-only demonstration: mutations are disabled')
        execution=bool(re.fullmatch(r'/api/v1/(experiments/[^/]+/runs|runs/[^/]+/cancel|research/projects/[^/]+/jobs|research/jobs/[^/]+/cancel|projects/[^/]+/experiments)',path))
        required='operator' if execution else 'admin'
        if {'viewer':0,'operator':1,'admin':2}[principal.role]<{'operator':1,'admin':2}[required]: raise HTTPException(403,required+' role required')

RATE_SCRIPT="""local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],65) end; return n"""
def rate_limit(identity,category,maximum,*,client=None,now=None):
    import redis
    client=client or redis.Redis.from_url(settings().broker_url,socket_connect_timeout=1,socket_timeout=1)
    key='failurelab:limit:'+category+':'+identity+':'+str(int((time.time() if now is None else now)//60))
    try: count=int(client.eval(RATE_SCRIPT,1,key))
    except redis.RedisError: raise HTTPException(503,'security rate limiter unavailable')
    if count>maximum: raise HTTPException(429,'request rate limit exceeded',headers={'Retry-After':'60'})

def request_route(request):
    route=getattr(request.scope.get('route'),'path','<unmatched>')
    return route[:200]
def save_audit(db,request,actor,status):
    resource=next((v for v in request.path_params.values() if isinstance(v,str) and re.fullmatch(r'[a-fA-F0-9-]{36}',v)),None)
    row=AuditEvent(actor_id=actor.actor_id if actor else 'anonymous',role=actor.role if actor else 'anonymous',method=request.method,route=request_route(request),resource_id=resource,status=status,request_id=request.state.request_id)
    db.add(row);db.commit();db.refresh(row)
    return row.id

def authenticate(request,authorization,db):
    policy=Policy.load(); actor=None
    try:
        if policy.mode!='local':
            peer=request.client.host if request.client else 'unknown'
            rate_limit(hashlib.sha256(peer.encode()).hexdigest(),'access',600)
        actor=policy.principal(authorization); policy.allow(actor,request.method,request.url.path)
        if request.method not in ('GET','HEAD','OPTIONS') and policy.mode!='local': rate_limit(actor.actor_id,'mutation',policy.mutations_per_minute)
    except HTTPException as exc:
        try: save_audit(db,request,actor,exc.status_code)
        except Exception:
            db.rollback()
            import logging
            logging.getLogger('failurelab').warning('Denied request audit unavailable; operation remained denied')
        raise
    request.state.principal=actor;request.state.policy=policy
    if request.method not in ('GET','HEAD','OPTIONS') or request.url.path.startswith('/api/v1/admin/'):
        try: request.state.audit_id=save_audit(db,request,actor,0)
        except Exception:
            db.rollback();raise HTTPException(503,'audit storage unavailable; operation was not authorized')
    return actor

def complete_audit(db,identity,status):
    db.execute(update(AuditEvent).where(AuditEvent.id==identity).values(status=status));db.commit()

class RequestContext:
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        state=scope.setdefault('state',{});state['request_id']=str(uuid.uuid4())
        async def wrapped(message):
            if message['type']=='http.response.start':
                state['response_status']=message['status']
                message['headers']=list(message.get('headers',[]))+[(b'x-request-id',state['request_id'].encode())]
            await send(message)
        await self.app(scope,receive,wrapped)
