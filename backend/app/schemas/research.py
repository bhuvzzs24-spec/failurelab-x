"""Versioned research contracts. Scores are acquisition utilities, never probabilities."""
from typing import Literal
from pydantic import Field, model_validator
from app.schemas.contracts import Contract

Defect = Literal['payment_ack_loss','unsafe_retry','lost_finalization','inventory_drift','concurrent_retry','failed_compensation']
Strategy = Literal['random','coverage','adaptive']
class Action(Contract):
    boundary: Literal['charge','reserve','finalize','refund']
    kind: Literal['latency','http_503','timeout']
    phase: Literal['before','after'] = 'after'
    delay_ms: int = Field(180,ge=0,le=500)
    at_ms: int = Field(0,ge=0,le=500)
    max_hits: int = Field(1,ge=1,le=2)
class Scenario(Contract):
    defect: Defect
    actions: list[Action] = Field(default_factory=list,max_length=2)
    amount: int = Field(100,ge=1,le=1000)
    quantity: int = Field(1,ge=1,le=5)
    concurrency: int = Field(1,ge=1,le=2)
    consistency_ms: int = Field(100,ge=50,le=500)
class SearchInput(Contract):
    strategy: Strategy = 'adaptive'
    budget: int = Field(12,ge=1,le=60)
    seed: int = Field(42,ge=0,le=2147483647)
    defects: list[Defect] = Field(default_factory=lambda:['payment_ack_loss','unsafe_retry','lost_finalization','inventory_drift','concurrent_retry','failed_compensation'],min_length=1,max_length=6)
class ResearchCreate(Contract):
    kind: Literal['SEARCH','MINIMIZE','INVESTIGATE','REPAIR','VERIFY','BENCHMARK']
    idempotency_key: str = Field(min_length=1,max_length=128,pattern=r'^[A-Za-z0-9_-]+$')
    search: SearchInput = Field(default_factory=SearchInput)
    source_trial_id: str | None = Field(None,max_length=36)
    candidate_id: str | None = Field(None,max_length=36)
    budget: int = Field(20,ge=2,le=100)
    repeats: int = Field(2,ge=2,le=5)
    seeds: list[int] = Field(default_factory=lambda:[17,42,93],min_length=2,max_length=5)
    @model_validator(mode='after')
    def prerequisites(self):
        if self.kind in ('MINIMIZE','INVESTIGATE','REPAIR') and not self.source_trial_id:
            raise ValueError('source_trial_id required')
        if self.kind=='VERIFY' and not self.candidate_id: raise ValueError('candidate_id required')
        if len(set(self.seeds))!=len(self.seeds) or any(not 0<=s<=2147483647 for s in self.seeds): raise ValueError('distinct bounded seeds required')
        return self
class ResearchJobOut(Contract):
    id: str
    project_id: str
    kind: str
    status: Literal['CREATED','QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED']
    created_at: float
    updated_at: float
    deadline: float
    input: ResearchCreate
    result: dict
    error: str | None
    cancel_requested: bool
class TrialOut(Contract):
    id: str
    job_id: str
    project_id: str
    created_at: float
    scenario: Scenario
    variant: Literal['original','reference']
    classification: Literal['APPLICATION_VIOLATION','NO_VIOLATION','INCONCLUSIVE','INFRASTRUCTURE_ERROR','INJECTION_NOT_OBSERVED']
    signature: str | None
    cost_seconds: float
    evidence: dict
class ResearchFindingOut(Contract):
    id: str
    project_id: str
    signature: str
    first_trial_id: str
    occurrences: int
    summary: str
class CandidateOut(Contract):
    id: str
    project_id: str
    source_trial_id: str
    created_at: float
    status: str
    patch: str
    metadata: dict
class ResearchArtifactOut(Contract):
    id: str
    job_id: str
    kind: str
    created_at: float
    sha256: str
    payload: dict
class DecisionOut(Contract):
    id: str
    job_id: str
    step: int
    context: dict
    scenario: Scenario
    score: float
    reward: float
    cost_seconds: float
class Hypothesis(Contract):
    id: str
    description: str
    services: list[str]
    assumptions: list[str]
    supporting_observations: list[str] = []
    contradicting_observations: list[str] = []
    intervention: str
    outcomes: list[dict] = []
    status: Literal['UNTESTED','SUPPORTED','REFUTED','INCONCLUSIVE'] = 'UNTESTED'
class MinimizeReport(Contract):
    original: Scenario
    reduced: Scenario
    removed_events: list[Action]
    attempts: list[dict]
    signature: str
    reproductions: int
    confirmation_trials: int
    local_minimality_tested: bool
    cost_seconds: float
    limitations: list[str]
class VerificationReport(Contract):
    outcome: Literal['ORIGINAL_FAILURE_REPRODUCED','PATCH_PASSES_TESTED_SCENARIOS','PATCH_FAILS_VERIFICATION','INCONCLUSIVE','INFRASTRUCTURE_ERROR']
    candidate_id: str
    cases: list[dict] = []
    environment: dict = {}
    limitations: list[str] = []
    reason: str | None = None
