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
    broker_transport_options={"visibility_timeout":900},
    beat_schedule={"dispatch-and-recover":{"task":"failurelab.dispatch","schedule":5.0}})

@celery.task(name="failurelab.run",bind=True,max_retries=None)
def execute(self,run_id):
    try: asyncio.run(Runner().run(run_id))
    except Busy: raise self.retry(countdown=2)

@celery.task(name="failurelab.dispatch")
def dispatch():
    asyncio.run(recover())
    dispatch_research()
    # Database outbox: API commit is durable even if Redis is temporarily down.
    with SessionLocal() as db:
        ids=list(db.scalars(select(Run.id).where((Run.status=="CREATED") | ((Run.status=="QUEUED") & (Run.updated_at<time.time()-15)))))
    for run_id in ids:
        with SessionLocal.begin() as db:
            changed=db.execute(update(Run).where(Run.id==run_id,Run.status.in_(["CREATED","QUEUED"])).values(status="QUEUED",updated_at=time.time())).rowcount
        if changed:
            Runner().event(run_id,"lifecycle",{"status":"QUEUED"})
            execute.apply_async(args=[run_id],task_id=run_id)


@celery.task(name="failurelab.research",bind=True,max_retries=None,soft_time_limit=610,time_limit=620)
def execute_research(self,job_id):
    from app.research.jobs import ResearchRunner, ResearchBusy
    try: asyncio.run(ResearchRunner().run(job_id))
    except ResearchBusy: raise self.retry(countdown=3)

def dispatch_research():
    from app.models.research import ResearchJob
    from app.research.jobs import recover_research
    recover_research()
    with SessionLocal() as db:
        ids=list(db.scalars(select(ResearchJob.id).where((ResearchJob.status=='CREATED') | ((ResearchJob.status=='QUEUED') & (ResearchJob.updated_at<time.time()-15)))))
    for job_id in ids:
        with SessionLocal.begin() as db:
            changed=db.execute(update(ResearchJob).where(ResearchJob.id==job_id,ResearchJob.status.in_(['CREATED','QUEUED'])).values(status='QUEUED',updated_at=time.time())).rowcount
        if changed: execute_research.apply_async(args=[job_id],task_id=job_id)
