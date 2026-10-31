import os
import asyncio
import time
from celery import Celery
from sqlalchemy import select, update
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.entities import Run
from app.experiments.runner import Runner, Busy, recover, TASK_HARD_LIMIT_SECONDS

from app.telemetry.logging import configure
configure()

celery=Celery("failurelab",broker=settings().broker_url)
celery.conf.update(task_default_queue=os.getenv("CELERY_QUEUE","failurelab"),task_acks_late=True,task_reject_on_worker_lost=True,worker_prefetch_multiplier=1,
    task_soft_time_limit=120,task_time_limit=TASK_HARD_LIMIT_SECONDS,broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout":180},
    beat_schedule={"dispatch-and-recover":{"task":"failurelab.dispatch","schedule":5.0}})

@celery.task(name="failurelab.run",bind=True,max_retries=None)
def execute(self,run_id):
    try: asyncio.run(Runner().run(run_id))
    except Busy: raise self.retry(countdown=2)

@celery.task(name="failurelab.dispatch")
def dispatch():
    asyncio.run(recover())
    # Database outbox: API commit is durable even if Redis is temporarily down.
    with SessionLocal() as db:
        ids=list(db.scalars(select(Run.id).where((Run.status=="CREATED") | ((Run.status=="QUEUED") & (Run.updated_at<time.time()-15)))))
    for run_id in ids:
        with SessionLocal.begin() as db:
            changed=db.execute(update(Run).where(Run.id==run_id,Run.status.in_(["CREATED","QUEUED"])).values(status="QUEUED",updated_at=time.time())).rowcount
        if changed:
            Runner().event(run_id,"lifecycle",{"status":"QUEUED"})
            execute.apply_async(args=[run_id],task_id=run_id)
