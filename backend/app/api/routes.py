import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.db import get_db
from app.models.entities import Project, Service, Dependency, Invariant, Experiment, Run, Artifact, Finding
from app.schemas.contracts import (ProjectCreate,ProjectOut,ServiceCreate,ServiceOut,DependencyCreate,
    DependencyOut,Graph,InvariantCreate,InvariantOut,ExperimentCreate,ExperimentOut,RunCreate,RunOut,
    ArtifactOut,FindingOut,Timeline,RunSummary,Page)
router=APIRouter(prefix="/api/v1")

def get(db,model,identity):
    row=db.get(model,identity)
    if row is None: raise HTTPException(404,"resource not found")
    return row

def save(db,item):
    db.add(item); db.commit(); db.refresh(item); return item

def page(db,model,schema,filters,offset,limit):
    rows=db.scalars(select(model).where(*filters).order_by(model.id).offset(offset).limit(limit))
    return Page(items=[schema.model_validate(row).model_dump() for row in rows],offset=offset,limit=limit,
                total=db.scalar(select(func.count()).select_from(model).where(*filters)))

@router.post("/projects",response_model=ProjectOut,status_code=201)
def create_project(body: ProjectCreate,db: Session=Depends(get_db)): return save(db,Project(**body.model_dump()))
@router.get("/projects",response_model=Page[ProjectOut])
def projects(offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db: Session=Depends(get_db)):
    return page(db,Project,ProjectOut,[],offset,limit)
@router.get("/projects/{project_id}",response_model=ProjectOut)
def project(project_id:str,db: Session=Depends(get_db)): return get(db,Project,project_id)
@router.post("/projects/{project_id}/services",response_model=ServiceOut,status_code=201)
def register_service(project_id:str,body:ServiceCreate,db: Session=Depends(get_db)):
    get(db,Project,project_id); return save(db,Service(project_id=project_id,**body.model_dump()))
@router.get("/projects/{project_id}/services",response_model=Page[ServiceOut])
def services(project_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Project,project_id); return page(db,Service,ServiceOut,[Service.project_id==project_id],offset,limit)
@router.post("/projects/{project_id}/dependencies",response_model=DependencyOut,status_code=201)
def dependency(project_id:str,body:DependencyCreate,db:Session=Depends(get_db)):
    get(db,Project,project_id)
    for identity in (body.source_id,body.target_id):
        if get(db,Service,identity).project_id!=project_id: raise HTTPException(422,"cross-project edge prohibited")
    if body.source_id==body.target_id: raise HTTPException(422,"self dependency prohibited")
    return save(db,Dependency(project_id=project_id,**body.model_dump()))
@router.get("/projects/{project_id}/graph",response_model=Graph)
def graph(project_id:str,db:Session=Depends(get_db)):
    get(db,Project,project_id)
    return Graph(nodes=[ServiceOut.model_validate(s) for s in db.scalars(select(Service).where(Service.project_id==project_id))],
        edges=[DependencyOut.model_validate(d) for d in db.scalars(select(Dependency).where(Dependency.project_id==project_id))])
@router.post("/projects/{project_id}/invariants",response_model=InvariantOut,status_code=201)
def invariant(project_id:str,body:InvariantCreate,db:Session=Depends(get_db)):
    get(db,Project,project_id); return save(db,Invariant(project_id=project_id,**body.model_dump()))
@router.get("/projects/{project_id}/invariants",response_model=Page[InvariantOut])
def invariants(project_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Project,project_id); return page(db,Invariant,InvariantOut,[Invariant.project_id==project_id],offset,limit)
@router.post("/projects/{project_id}/experiments",response_model=ExperimentOut,status_code=201)
def experiment(project_id:str,body:ExperimentCreate,db:Session=Depends(get_db)):
    get(db,Project,project_id)
    names=set(db.scalars(select(Service.name).where(Service.project_id==project_id)))
    if names!={"gateway","order","payment","inventory"}: raise HTTPException(422,"register all four sandbox services first")
    for identity in body.config.invariant_ids:
        if get(db,Invariant,identity).project_id!=project_id: raise HTTPException(422,"cross-project invariant prohibited")
    return save(db,Experiment(project_id=project_id,**body.model_dump()))
@router.get("/projects/{project_id}/experiments",response_model=Page[ExperimentOut])
def experiments(project_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Project,project_id); return page(db,Experiment,ExperimentOut,[Experiment.project_id==project_id],offset,limit)
@router.get("/experiments/{experiment_id}",response_model=ExperimentOut)
def get_experiment(experiment_id:str,db:Session=Depends(get_db)): return get(db,Experiment,experiment_id)
@router.post("/experiments/{experiment_id}/runs",response_model=RunOut,status_code=202)
def start(experiment_id:str,body:RunCreate,db:Session=Depends(get_db)):
    experiment=get(db,Experiment,experiment_id)
    previous=db.scalar(select(Run).where(Run.experiment_id==experiment_id,Run.idempotency_key==body.idempotency_key))
    if previous: return previous
    # Persist outbox before publication; periodic dispatcher retries broker outages.
    try:
        row=save(db,Run(experiment_id=experiment_id,idempotency_key=body.idempotency_key,
                      config=experiment.config,deadline=time.time()+experiment.config["max_duration_seconds"]))
    except IntegrityError:
        db.rollback()
        existing=db.scalar(select(Run).where(Run.experiment_id==experiment_id,Run.idempotency_key==body.idempotency_key))
        if existing: return existing
        raise
    from app.repositories.evidence import artifact
    artifact(db,row.id,"lifecycle",{"status":"CREATED"})
    return row
@router.get("/experiments/{experiment_id}/runs",response_model=Page[RunOut])
def runs(experiment_id:str,status:str|None=Query(None,pattern=r"^(CREATED|QUEUED|RUNNING|VERIFYING|COMPLETED|FAILED|CANCELLED)$"),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Experiment,experiment_id); filters=[Run.experiment_id==experiment_id]
    if status: filters.append(Run.status==status)
    return page(db,Run,RunOut,filters,offset,limit)
@router.get("/runs/{run_id}",response_model=RunOut)
def run(run_id:str,db:Session=Depends(get_db)): return get(db,Run,run_id)
@router.post("/runs/{run_id}/cancel",response_model=RunOut)
def cancel(run_id:str,db:Session=Depends(get_db)):
    row=get(db,Run,run_id)
    if row.status in {"COMPLETED","FAILED","CANCELLED"}: raise HTTPException(409,"run already terminal")
    row.cancel_requested=1; row.updated_at=time.time(); db.commit(); return row
@router.get("/runs/{run_id}/artifacts",response_model=Page[ArtifactOut])
def artifacts(run_id:str,kind:str|None=Query(None,max_length=40),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Run,run_id); filters=[Artifact.run_id==run_id]
    if kind: filters.append(Artifact.kind==kind)
    return page(db,Artifact,ArtifactOut,filters,offset,limit)
@router.get("/artifacts/{artifact_id}",response_model=ArtifactOut)
def artifact_get(artifact_id:str,db:Session=Depends(get_db)): return get(db,Artifact,artifact_id)
@router.get("/runs/{run_id}/findings",response_model=Page[FindingOut])
def findings(run_id:str,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    get(db,Run,run_id); return page(db,Finding,FindingOut,[Finding.run_id==run_id],offset,limit)
@router.get("/runs/{run_id}/timeline",response_model=Timeline)
def timeline(run_id:str,db:Session=Depends(get_db)):
    get(db,Run,run_id)
    return Timeline(events=[ArtifactOut.model_validate(a) for a in db.scalars(select(Artifact).where(Artifact.run_id==run_id).order_by(Artifact.created_at,Artifact.id))])
@router.get("/runs/{run_id}/summary",response_model=RunSummary)
def summary(run_id:str,db:Session=Depends(get_db)):
    row=get(db,Run,run_id)
    return RunSummary(run=RunOut.model_validate(row),
        findings=[FindingOut.model_validate(f) for f in db.scalars(select(Finding).where(Finding.run_id==run_id))],
        artifacts=timeline(run_id,db).events)
