"""Additive project-wide read models. Counts cover the entire project, not a page."""
from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.config import settings, ALLOWED_SERVICES
from app.models.entities import Project, Service, Experiment, Run, Finding, Artifact
from app.models.research import ResearchJob, ResearchFinding
from app.schemas.contracts import Page, RunOut, FindingOut, Fault, ExperimentConfig
from app.schemas.overview import ProjectOverview, ActivityPoint, Capabilities
from app.api.routes import get

router=APIRouter(prefix="/api/v1")
ACTIVE={"CREATED","QUEUED","RUNNING","VERIFYING"}
RunStatus=Literal["CREATED","QUEUED","RUNNING","VERIFYING","COMPLETED","FAILED","CANCELLED"]

@router.get("/capabilities",response_model=Capabilities)
def capabilities():
    fault=Fault.model_json_schema()["properties"]
    config=ExperimentConfig.model_json_schema()["properties"]
    return Capabilities(sandbox_id=settings().sandbox,engine_version=settings().version,
        allowed_services=sorted(ALLOWED_SERVICES),fault_targets=[fault["target"]["const"]],
        fault_kinds=fault["kind"]["enum"],max_fault_seconds=fault["duration_seconds"]["maximum"],
        max_run_seconds=config["max_duration_seconds"]["maximum"],automatic_replay=False,
        causal_analysis=False,minimization=False,repair_verification=False,logs_inline=False)

@router.get("/projects/{project_id}/overview",response_model=ProjectOverview)
def overview(project_id:str,db:Session=Depends(get_db)):
    get(db,Project,project_id)
    ids=select(Experiment.id).where(Experiment.project_id==project_id)
    run_ids=select(Run.id).where(Run.experiment_id.in_(ids))
    counts=dict(db.execute(select(Run.status,func.count()).where(Run.experiment_id.in_(ids)).group_by(Run.status)).all())
    today=datetime.now(timezone.utc).date()
    start=today-timedelta(days=13)
    daily={(start+timedelta(days=i)).isoformat():0 for i in range(14)}
    start_epoch=datetime.combine(start,datetime.min.time(),tzinfo=timezone.utc).timestamp()
    for stamp in db.scalars(select(Run.created_at).where(Run.experiment_id.in_(ids),Run.created_at>=start_epoch)):
        day=datetime.fromtimestamp(stamp,timezone.utc).date().isoformat()
        if day in daily: daily[day]+=1
    latest=list(db.scalars(select(Run).where(Run.experiment_id.in_(ids)).order_by(Run.created_at.desc(),Run.id).limit(12)))
    findings=list(db.scalars(select(Finding).join(Run,Finding.run_id==Run.id).where(Run.experiment_id.in_(ids)).order_by(Run.created_at.desc(),Finding.id).limit(8)))
    def count(model,predicate): return db.scalar(select(func.count()).select_from(model).where(predicate))
    return ProjectOverview(research_job_count=count(ResearchJob,ResearchJob.project_id==project_id),
        active_research_count=db.scalar(select(func.count()).select_from(ResearchJob).where(ResearchJob.project_id==project_id,ResearchJob.status.in_(['CREATED','QUEUED','RUNNING']))),
        research_violation_count=count(ResearchFinding,ResearchFinding.project_id==project_id),service_count=count(Service,Service.project_id==project_id),
        experiment_count=count(Experiment,Experiment.project_id==project_id),run_count=sum(counts.values()),
        active_run_count=sum(value for key,value in counts.items() if key in ACTIVE),
        violation_count=count(Finding,Finding.run_id.in_(run_ids)),artifact_count=count(Artifact,Artifact.run_id.in_(run_ids)),
        status_counts=counts,activity=[ActivityPoint(day=day,runs=value) for day,value in daily.items()],
        latest_runs=[RunOut.model_validate(row) for row in latest],latest_findings=[FindingOut.model_validate(row) for row in findings])

@router.get("/projects/{project_id}/runs",response_model=Page[RunOut])
def project_runs(project_id:str,status:RunStatus|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Project,project_id)
    ids=select(Experiment.id).where(Experiment.project_id==project_id)
    filters=[Run.experiment_id.in_(ids)]
    if status: filters.append(Run.status==status)
    rows=db.scalars(select(Run).where(*filters).order_by(Run.created_at.desc(),Run.id).offset(offset).limit(limit))
    return Page[RunOut](items=[RunOut.model_validate(row) for row in rows],offset=offset,limit=limit,
        total=db.scalar(select(func.count()).select_from(Run).where(*filters)))

@router.get("/projects/{project_id}/findings",response_model=Page[FindingOut])
def project_findings(project_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Project,project_id)
    ids=select(Experiment.id).where(Experiment.project_id==project_id)
    query=select(Finding).join(Run,Finding.run_id==Run.id).where(Run.experiment_id.in_(ids))
    rows=db.scalars(query.order_by(Run.created_at.desc(),Finding.id).offset(offset).limit(limit))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    return Page[FindingOut](items=[FindingOut.model_validate(row) for row in rows],offset=offset,limit=limit,total=total)
