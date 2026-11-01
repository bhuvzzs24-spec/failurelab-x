"""Append-only request intents, completed with actual response status; never bodies/tokens."""
import time
import uuid
from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base
class AuditEvent(Base):
    __tablename__='audit_events'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    created_at: Mapped[float]=mapped_column(Float,default=time.time,index=True)
    actor_id: Mapped[str]=mapped_column(String(64),index=True)
    role: Mapped[str]=mapped_column(String(20))
    method: Mapped[str]=mapped_column(String(8))
    route: Mapped[str]=mapped_column(String(200))
    resource_id: Mapped[str|None]=mapped_column(String(36),nullable=True)
    status: Mapped[int]=mapped_column(Integer,default=0)
    request_id: Mapped[str]=mapped_column(String(36))
