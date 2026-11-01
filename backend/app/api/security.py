from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.audit import AuditEvent
from app.schemas.security import SessionOut,AuditOut
from app.schemas.contracts import Page
router=APIRouter(prefix='/api/v1')
@router.get('/session',response_model=SessionOut)
def session(request:Request):
    actor=request.state.principal;policy=request.state.policy
    return SessionOut(role=actor.role,mode=policy.mode,read_only=policy.mode=='read_only' or actor.role=='viewer',can_execute=policy.mode!='read_only' and actor.role in ('operator','admin'),can_manage=policy.mode!='read_only' and actor.role=='admin')
@router.get('/admin/audit',response_model=Page[AuditOut])
def audit(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    rows=db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc(),AuditEvent.id).offset(offset).limit(limit))
    return Page(items=[AuditOut.model_validate(r) for r in rows],total=db.scalar(select(func.count()).select_from(AuditEvent)),offset=offset,limit=limit)
