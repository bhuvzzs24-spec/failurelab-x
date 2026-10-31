"""Real Redis transport and worker processes; no eager Celery execution."""
import os
import shutil
import subprocess
import sys
import time
import uuid
import pytest
import redis
from celery import Celery
from sqlalchemy import select
from app.models.entities import Run, Artifact, Finding
from conftest import free_port, ROOT


def test_redis_dispatch_and_worker_restart(sessions,make_run,live_demo,tmp_path):
    origins,base_env,_=live_demo
    broker=os.getenv("TEST_REDIS_URL")
    redis_process=None
    redis_log=open(tmp_path/"redis.log","w")
    if not broker:
        binary=shutil.which("redis-server")
        if not binary:
            pytest.skip("Redis integration requires redis-server or explicit TEST_REDIS_URL; no fake broker fallback")
        port=free_port(); broker=f"redis://127.0.0.1:{port}/0"
        redis_process=subprocess.Popen([binary,"--bind","127.0.0.1","--port",str(port),"--save","","--appendonly","no","--dir",str(tmp_path)],stdout=redis_log,stderr=redis_log)
    connection=redis.Redis.from_url(broker)
    deadline=time.monotonic()+10
    while True:
        try:
            if connection.ping(): break
        except redis.ConnectionError: pass
        if time.monotonic()>deadline: pytest.fail("Redis did not start")
        time.sleep(.05)
    queue="test-"+uuid.uuid4().hex
    env={**base_env,"DATABASE_URL":str(sessions.kw["bind"].url),"REDIS_URL":broker,"CELERY_QUEUE":queue}
    publisher=Celery("integration-publisher",broker=broker)
    workers=[]; logs=[]
    def worker():
        log=open(tmp_path/("worker-"+str(len(workers))+".log"),"w"); logs.append(log)
        process=subprocess.Popen([sys.executable,"-m","celery","-A","app.workers.tasks.celery","worker","--pool=solo","--loglevel=INFO","--without-gossip","--without-mingle","--without-heartbeat","-Q",queue],cwd=ROOT,env=env,stdout=log,stderr=log)
        workers.append(process); return process
    def wait_until(predicate,seconds=25):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            with sessions() as db:
                if predicate(db): return
            time.sleep(.05)
        text="\n".join(p.read_text()[-5000:] for p in tmp_path.glob("worker-*.log"))
        pytest.fail("worker condition timed out\n"+text)
    try:
        process=worker()
        # Warm broker imports and wait for a genuinely ready worker before the
        # bounded business experiment is created. Startup latency is not run time.
        publisher.send_task("failurelab.dispatch",queue=queue)
        ready_deadline=time.monotonic()+60
        while "ready." not in (tmp_path/"worker-0.log").read_text():
            if process.poll() is not None or time.monotonic()>ready_deadline:
                pytest.fail("Celery worker failed startup: "+(tmp_path/"worker-0.log").read_text())
            time.sleep(.05)
        first=make_run()
        publisher.send_task("failurelab.dispatch",queue=queue)
        wait_until(lambda db: db.get(Run,first).status in {"COMPLETED","FAILED"})
        with sessions() as db:
            assert db.get(Run,first).status=="COMPLETED",db.get(Run,first).result
            assert db.scalar(select(Finding).where(Finding.run_id==first))
        second=make_run(consistency=8)
        publisher.send_task("failurelab.dispatch",queue=queue)
        wait_until(lambda db: db.scalar(select(Artifact).where(Artifact.run_id==second,Artifact.kind=="fault_schedule")) is not None)
        process.kill(); process.wait(timeout=5)  # genuine abnormal worker termination
        with sessions.begin() as db: db.get(Run,second).deadline=time.time()-1
        worker()
        publisher.send_task("failurelab.dispatch",queue=queue)
        wait_until(lambda db: db.get(Run,second).status=="FAILED")
        with sessions() as db:
            row=db.get(Run,second)
            assert row.result["cleanup_confirmed"]
            assert db.scalar(select(Artifact).where(Artifact.run_id==second,Artifact.kind=="recovery"))
    finally:
        for process in workers:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
        for log in logs: log.close()
        publisher.close(); connection.delete(queue); connection.close()
        if redis_process:
            redis_process.terminate(); redis_process.wait(timeout=5)
        redis_log.close()
