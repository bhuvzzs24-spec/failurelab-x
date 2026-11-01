"""Authenticated local research API; no host, command or patch path input."""
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.api.routes import get, page, save
from app.models.entities import Project, Service
from app.models.research import ResearchJob, ResearchTrial, ResearchFinding, ResearchDecision, RepairCandidate, ResearchArtifact
from app.schemas.research import ResearchCreate,ResearchJobOut,TrialOut,ResearchFindingOut,DecisionOut,CandidateOut,ResearchArtifactOut
from app.schemas.contracts import Page
router=APIRouter(prefix='/api/v1/research')
@router.get('/capabilities')
def capabilities():
    import os
    from app.benchmarks.catalog import DEFECTS
    return {'sandbox':'managed-benchmark','defects':DEFECTS,'strategies':['random','coverage','adaptive'],'candidate_execution':'restricted_docker_agent','repair_agent_configured':bool(os.getenv('REPAIR_AGENT_URL')),'llm_enabled':bool(os.getenv('OLLAMA_URL')),'max_job_seconds':600,'max_actions':2,'repair_scope':'literal benchmark recovery policies','arbitrary_repository_repair':False}
@router.post('/projects/{project_id}/jobs',response_model=ResearchJobOut,status_code=202)
def create(project_id:str,body:ResearchCreate,db:Session=Depends(get_db)):
    get(db,Project,project_id)
    names=set(db.scalars(select(Service.name).where(Service.project_id==project_id)))
    if names!={'gateway','order','payment','inventory'}: raise HTTPException(422,'register all four managed sandbox services first')
    existing=db.scalar(select(ResearchJob).where(ResearchJob.project_id==project_id,ResearchJob.idempotency_key==body.idempotency_key))
    if existing:
        if existing.input!=body.model_dump(): raise HTTPException(409,'idempotency key payload mismatch')
        return existing
    if body.source_trial_id:
        source=get(db,ResearchTrial,body.source_trial_id)
        if source.project_id!=project_id or source.variant!='original' or source.classification!='APPLICATION_VIOLATION': raise HTTPException(422,'original project violation trial required')
    if body.candidate_id and get(db,RepairCandidate,body.candidate_id).project_id!=project_id: raise HTTPException(422,'cross-project candidate prohibited')
    return save(db,ResearchJob(project_id=project_id,idempotency_key=body.idempotency_key,kind=body.kind,input=body.model_dump(),deadline=time.time()+600))
@router.get('/projects/{project_id}/jobs',response_model=Page[ResearchJobOut])
def jobs(project_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Project,project_id); return page(db,ResearchJob,ResearchJobOut,[ResearchJob.project_id==project_id],offset,limit)
@router.get('/jobs/{job_id}',response_model=ResearchJobOut)
def job(job_id:str,db:Session=Depends(get_db)): return get(db,ResearchJob,job_id)
@router.post('/jobs/{job_id}/cancel',response_model=ResearchJobOut)
def cancel(job_id:str,db:Session=Depends(get_db)):
    row=get(db,ResearchJob,job_id)
    # Compare-and-set prevents a stale queued read from overwriting a worker claim.
    db.execute(update(ResearchJob).where(ResearchJob.id==job_id,ResearchJob.status.in_(['CREATED','QUEUED'])).values(cancel_requested=1,status='CANCELLED',updated_at=time.time()))
    db.execute(update(ResearchJob).where(ResearchJob.id==job_id,ResearchJob.status=='RUNNING').values(cancel_requested=1,updated_at=time.time()))
    db.commit(); db.refresh(row)
    return row
@router.get('/projects/{project_id}/trials',response_model=Page[TrialOut])
def trials(project_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Project,project_id); return page(db,ResearchTrial,TrialOut,[ResearchTrial.project_id==project_id],offset,limit)
@router.get('/trials/{trial_id}',response_model=TrialOut)
def trial(trial_id:str,db:Session=Depends(get_db)): return get(db,ResearchTrial,trial_id)
@router.get('/projects/{project_id}/findings',response_model=Page[ResearchFindingOut])
def findings(project_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Project,project_id); return page(db,ResearchFinding,ResearchFindingOut,[ResearchFinding.project_id==project_id],offset,limit)
@router.get('/jobs/{job_id}/decisions',response_model=Page[DecisionOut])
def decisions(job_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,ResearchJob,job_id); return page(db,ResearchDecision,DecisionOut,[ResearchDecision.job_id==job_id],offset,limit)
@router.get('/jobs/{job_id}/artifacts',response_model=Page[ResearchArtifactOut])
def artifacts(job_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,ResearchJob,job_id); return page(db,ResearchArtifact,ResearchArtifactOut,[ResearchArtifact.job_id==job_id],offset,limit)
def candidate_out(row):
    return CandidateOut(id=row.id,project_id=row.project_id,source_trial_id=row.source_trial_id,created_at=row.created_at,status=row.status,patch=row.patch,metadata=row.details)
@router.get('/projects/{project_id}/candidates',response_model=Page[CandidateOut])
def candidates(project_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Project,project_id)
    from sqlalchemy import func
    filters=[RepairCandidate.project_id==project_id]
    return Page(items=[candidate_out(r) for r in db.scalars(select(RepairCandidate).where(*filters).order_by(RepairCandidate.created_at.desc()).offset(offset).limit(limit))],offset=offset,limit=limit,total=db.scalar(select(func.count()).select_from(RepairCandidate).where(*filters)))
@router.get('/candidates/{candidate_id}',response_model=CandidateOut)
def candidate(candidate_id:str,db:Session=Depends(get_db)): return candidate_out(get(db,RepairCandidate,candidate_id))
