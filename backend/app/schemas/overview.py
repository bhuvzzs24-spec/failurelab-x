from app.schemas.contracts import Contract, RunOut, FindingOut

class ActivityPoint(Contract):
    day: str
    runs: int

class ProjectOverview(Contract):
    service_count: int
    experiment_count: int
    run_count: int
    active_run_count: int
    violation_count: int
    artifact_count: int
    status_counts: dict[str, int]
    activity: list[ActivityPoint]
    latest_runs: list[RunOut]
    latest_findings: list[FindingOut]

class Capabilities(Contract):
    sandbox_id: str
    engine_version: str
    allowed_services: list[str]
    fault_targets: list[str]
    fault_kinds: list[str]
    max_fault_seconds: float
    max_run_seconds: int
    automatic_replay: bool
    causal_analysis: bool
    minimization: bool
    repair_verification: bool
    logs_inline: bool
