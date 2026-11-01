from typing import Literal
from app.schemas.contracts import Contract
class SessionOut(Contract):
    role: Literal['viewer','operator','admin']
    mode: Literal['local','hosted','read_only']
    read_only: bool
    can_execute: bool
    can_manage: bool
class AuditOut(Contract):
    id: str
    created_at: float
    actor_id: str
    role: str
    method: str
    route: str
    resource_id: str|None
    status: int
    request_id: str
