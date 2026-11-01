import time
import uuid
from sqlalchemy import String, Float, Integer, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

def uid(): return str(uuid.uuid4())
class ResearchJob(Base):
    __tablename__='research_jobs'
    __table_args__=(UniqueConstraint('project_id','idempotency_key'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    idempotency_key: Mapped[str]=mapped_column(String(128))
    kind: Mapped[str]=mapped_column(String(20))
    status: Mapped[str]=mapped_column(String(20),default='CREATED',index=True)
    created_at: Mapped[float]=mapped_column(Float,default=time.time)
    updated_at: Mapped[float]=mapped_column(Float,default=time.time)
    deadline: Mapped[float]=mapped_column(Float)
    owner: Mapped[str|None]=mapped_column(String(36),nullable=True)
    cancel_requested: Mapped[int]=mapped_column(Integer,default=0)
    input: Mapped[dict]=mapped_column(JSON)
    result: Mapped[dict]=mapped_column(JSON,default=dict)
    error: Mapped[str|None]=mapped_column(String(500),nullable=True)
class ResearchTrial(Base):
    __tablename__='research_trials'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    job_id: Mapped[str]=mapped_column(ForeignKey('research_jobs.id'),index=True)
    project_id: Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    created_at: Mapped[float]=mapped_column(Float,default=time.time)
    scenario: Mapped[dict]=mapped_column(JSON)
    variant: Mapped[str]=mapped_column(String(20))
    classification: Mapped[str]=mapped_column(String(40))
    signature: Mapped[str|None]=mapped_column(String(64),nullable=True,index=True)
    cost_seconds: Mapped[float]=mapped_column(Float)
    evidence: Mapped[dict]=mapped_column(JSON)
class ResearchFinding(Base):
    __tablename__='research_findings'
    __table_args__=(UniqueConstraint('project_id','signature'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    signature: Mapped[str]=mapped_column(String(64))
    first_trial_id: Mapped[str]=mapped_column(ForeignKey('research_trials.id'))
    occurrences: Mapped[int]=mapped_column(Integer,default=1)
    summary: Mapped[str]=mapped_column(String(300))
class ResearchDecision(Base):
    __tablename__='research_decisions'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    job_id: Mapped[str]=mapped_column(ForeignKey('research_jobs.id'),index=True)
    step: Mapped[int]=mapped_column(Integer)
    context: Mapped[dict]=mapped_column(JSON)
    scenario: Mapped[dict]=mapped_column(JSON)
    score: Mapped[float]=mapped_column(Float)
    reward: Mapped[float]=mapped_column(Float)
    cost_seconds: Mapped[float]=mapped_column(Float)
class RepairCandidate(Base):
    __tablename__='repair_candidates'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    source_trial_id: Mapped[str]=mapped_column(ForeignKey('research_trials.id'))
    created_at: Mapped[float]=mapped_column(Float,default=time.time)
    status: Mapped[str]=mapped_column(String(40),default='PREPARED')
    patch: Mapped[str]=mapped_column(String(20000))
    # `metadata` is reserved by SQLAlchemy.
    details: Mapped[dict]=mapped_column('metadata',JSON)
class ResearchArtifact(Base):
    __tablename__='research_artifacts'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    job_id: Mapped[str]=mapped_column(ForeignKey('research_jobs.id'),index=True)
    kind: Mapped[str]=mapped_column(String(40))
    created_at: Mapped[float]=mapped_column(Float,default=time.time)
    sha256: Mapped[str]=mapped_column(String(64))
    payload: Mapped[dict]=mapped_column(JSON)
