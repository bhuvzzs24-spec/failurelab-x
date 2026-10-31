import uuid
import time
from sqlalchemy import String, Float, JSON, ForeignKey, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

def uid(): return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)

class Service(Base):
    __tablename__ = "services"
    __table_args__ = (UniqueConstraint("project_id", "name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(128))
    operations: Mapped[list] = mapped_column(JSON, default=list)
    resources: Mapped[list] = mapped_column(JSON, default=list)

class Dependency(Base):
    __tablename__ = "dependencies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    source_id: Mapped[str] = mapped_column(ForeignKey("services.id"))
    target_id: Mapped[str] = mapped_column(ForeignKey("services.id"))
    kind: Mapped[str] = mapped_column(String(32))
    operation: Mapped[str] = mapped_column(String(160))
    workflow: Mapped[str] = mapped_column(String(80))

class Invariant(Base):
    __tablename__ = "invariants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(120))
    rule: Mapped[dict] = mapped_column(JSON)

class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(120))
    config: Mapped[dict] = mapped_column(JSON)

class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (UniqueConstraint("experiment_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20), default="CREATED", index=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)
    deadline: Mapped[float] = mapped_column(Float)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    owner: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cancel_requested: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, default=dict)

class SandboxLease(Base):
    __tablename__ = "sandbox_leases"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expires_at: Mapped[float] = mapped_column(Float, default=0)

class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    sha256: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)

class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    invariant_id: Mapped[str] = mapped_column(ForeignKey("invariants.id"))
    summary: Mapped[str] = mapped_column(String(300))
    evidence: Mapped[dict] = mapped_column(JSON)
