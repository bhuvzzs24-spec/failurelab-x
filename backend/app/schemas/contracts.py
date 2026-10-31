from typing import Literal, Annotated, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

class ProjectCreate(Contract):
    name: str = Field(min_length=1, max_length=120)
class ProjectOut(ProjectCreate):
    id: str
    created_at: float
class Operation(Contract):
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path: str = Field(pattern=r"^/[a-zA-Z0-9_/{}/-]{0,150}$")
class ServiceCreate(Contract):
    name: Literal["gateway", "order", "payment", "inventory"]
    version: str = Field(min_length=1, max_length=128)
    operations: list[Operation] = Field(default_factory=list, max_length=30)
    resources: list[Annotated[str, Field(max_length=128)]] = Field(default_factory=list, max_length=20)
class ServiceOut(ServiceCreate):
    id: str
    project_id: str
class DependencyCreate(Contract):
    source_id: str
    target_id: str
    kind: Literal["http", "shared_resource", "workflow"]
    operation: str = Field(max_length=160)
    workflow: str = Field(max_length=80)
class DependencyOut(DependencyCreate):
    id: str
    project_id: str
class Graph(Contract):
    nodes: list[ServiceOut]
    edges: list[DependencyOut]
    provenance: Literal["explicit_registration"] = "explicit_registration"

StatePath = Annotated[str, Field(pattern=r"^(order|payment|inventory)\.(status|amount|quantity)$")]
class Operand(Contract):
    path: StatePath | None = None
    value: Annotated[str, Field(max_length=128)] | int | bool | None = None
    @model_validator(mode="after")
    def exactly_one(self):
        if self.path is not None and self.value is not None: raise ValueError("choose path or literal")
        return self
class Compare(Contract):
    kind: Literal["compare"] = "compare"
    left: Operand
    op: Literal["eq", "ne", "gte", "lte"] = "eq"
    right: Operand
class Implication(Contract):
    kind: Literal["implies"] = "implies"
    antecedent: Compare
    consequent: Compare
class Transition(Contract):
    kind: Literal["transition"] = "transition"
    path: StatePath
    allowed: list[tuple[str, str]] = Field(min_length=1, max_length=30)
Rule = Annotated[Compare | Implication | Transition, Field(discriminator="kind")]
class InvariantCreate(Contract):
    name: str = Field(min_length=1,max_length=120)
    rule: Rule
class InvariantOut(InvariantCreate):
    id: str
    project_id: str
class Fault(Contract):
    target: Literal["payment"] = "payment"
    kind: Literal["latency", "timeout", "http_503", "reset", "unavailable", "worker_interrupt"]
    delay_seconds: float = Field(default=1.5, ge=0, le=10)
    duration_seconds: float = Field(default=10, ge=1, le=30)
    phase: Literal["before", "after"] = "after"
class ExperimentConfig(Contract):
    fault: Fault
    invariant_ids: list[str] = Field(min_length=1,max_length=20)
    seed: int = Field(default=42,ge=0,le=2147483647)
    max_duration_seconds: int = Field(default=45,ge=10,le=90)
    consistency_seconds: float = Field(default=2,ge=0,le=15)
    retry_seconds: float = Field(default=.2,ge=.05,le=2)
    amount: int = Field(default=100,ge=1,le=10000)
    quantity: int = Field(default=1,ge=1,le=10)
    @model_validator(mode="after")
    def budget(self):
        if self.fault.duration_seconds + self.consistency_seconds + 5 > self.max_duration_seconds:
            raise ValueError("deadline must accommodate fault TTL, verification and cleanup")
        return self
class ExperimentCreate(Contract):
    name: str = Field(min_length=1,max_length=120)
    config: ExperimentConfig
class ExperimentOut(ExperimentCreate):
    id: str
    project_id: str
class RunCreate(Contract):
    idempotency_key: str = Field(min_length=1,max_length=128,pattern=r"^[a-zA-Z0-9_-]+$")
class RunOut(Contract):
    id: str
    experiment_id: str
    idempotency_key: str
    status: Literal["CREATED","QUEUED","RUNNING","VERIFYING","COMPLETED","FAILED","CANCELLED"]
    created_at: float
    updated_at: float
    deadline: float
    cancel_requested: int
    config: dict
    result: dict
class Evaluation(Contract):
    status: Literal["PASS", "FAIL", "INCONCLUSIVE"]
    observed: dict
    expected: dict
    evidence_refs: list[str]
    evaluated_at: float
    reason: str | None = None
class ArtifactOut(Contract):
    id: str
    run_id: str
    kind: str
    created_at: float
    sha256: str
    payload: dict
class FindingOut(Contract):
    id: str
    run_id: str
    invariant_id: str
    summary: str
    evidence: dict
class Timeline(Contract):
    events: list[ArtifactOut]
class RunSummary(Contract):
    run: RunOut
    findings: list[FindingOut]
    artifacts: list[ArtifactOut]
T = TypeVar("T")
class Page(Contract, Generic[T]):
    items: list[T]
    offset: int
    limit: int
    total: int
class ErrorDetail(Contract):
    code: str
    message: str
class ErrorResponse(Contract):
    error: ErrorDetail
