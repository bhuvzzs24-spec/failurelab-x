import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from dataclasses import replace
import httpx
import pytest
from sqlalchemy.orm import sessionmaker
from app.core.db import Base, make_engine
from app.core.config import settings
from app.models.entities import SandboxLease,Project,Service,Invariant,Experiment,Run

ROOT=Path(__file__).resolve().parents[2]
RULE={"kind":"implies","antecedent":{"kind":"compare","left":{"path":"payment.status"},"op":"eq","right":{"value":"charged"}},"consequent":{"kind":"compare","left":{"path":"order.status"},"op":"eq","right":{"value":"finalized"}}}

@pytest.fixture
def sessions(tmp_path):
    engine=make_engine("sqlite:///"+str(tmp_path/"lab.db"))
    Base.metadata.create_all(engine)
    sessions=sessionmaker(engine,expire_on_commit=False)
    with sessions.begin() as db: db.add(SandboxLease(id="demo",expires_at=0))
    yield sessions
    engine.dispose()

@pytest.fixture
def make_run(sessions):
    def create(kind="latency",delay=1.5,phase="after",consistency=.2):
        with sessions.begin() as db:
            project=Project(name="demo_"+str(time.time_ns())); db.add(project); db.flush()
            for name in ("gateway","order","payment","inventory"):
                db.add(Service(project_id=project.id,name=name,version="test"))
            invariant=Invariant(project_id=project.id,name="paid implies ordered",rule=RULE); db.add(invariant); db.flush()
            config={"fault":{"kind":kind,"target":"payment","phase":phase,"delay_seconds":delay,"duration_seconds":2},"invariant_ids":[invariant.id],"max_duration_seconds":30,"consistency_seconds":consistency,"retry_seconds":.05,"amount":100,"quantity":1,"seed":42}
            experiment=Experiment(project_id=project.id,name="discovery",config=config); db.add(experiment); db.flush()
            run=Run(experiment_id=experiment.id,idempotency_key="test",config=config,deadline=time.time()+30); db.add(run); db.flush()
            return run.id
    return create

def free_port():
    with socket.socket() as sock: sock.bind(("127.0.0.1",0)); return sock.getsockname()[1]

@pytest.fixture(scope="session")
def live_demo(tmp_path_factory):
    folder=tmp_path_factory.mktemp("demo")
    ports={name:free_port() for name in ("gateway","order","payment","inventory","proxy","proxy_control")}
    origins={name:"http://127.0.0.1:"+str(port) for name,port in ports.items()}
    env=os.environ.copy(); env["PYTHONPATH"]=str(ROOT/"backend")
    for name,url in origins.items(): env[name.upper()+"_URL"]=url
    env.update(CONTROL_TOKEN="integration-control",BUILD_VERSION="integration-tests",DATA_PORT=str(ports["proxy"]),CONTROL_PORT=str(ports["proxy_control"]))
    processes=[]; handles=[]
    try:
        for role in ("order","payment","inventory","gateway","proxy"):
            handle=open(folder/(role+".log"),"w"); handles.append(handle)
            local=env.copy(); local["DEMO_ROLE"]=role
            local["DEMO_DATABASE_URL"]="sqlite:///"+str(folder/(role+".db"))
            command=[sys.executable,"-m","app.faults.proxy"] if role=="proxy" else [sys.executable,"-m","uvicorn","app.services.demo:create_app","--factory","--host","127.0.0.1","--port",str(ports[role]),"--no-access-log"]
            processes.append(subprocess.Popen(command,cwd=ROOT,env=local,stdout=handle,stderr=handle))
            health=origins["proxy_control" if role=="proxy" else role]+"/health"
            deadline=time.monotonic()+15
            while True:
                try:
                    with httpx.Client(trust_env=False,timeout=.2) as client:
                        if client.get(health).status_code==200: break
                except httpx.HTTPError: pass
                if time.monotonic()>deadline: raise RuntimeError((folder/(role+".log")).read_text())
                time.sleep(.05)
        yield origins,env,folder
    finally:
        for process in processes: process.terminate()
        for process in processes:
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        for handle in handles: handle.close()

@pytest.fixture
def sandbox(live_demo,monkeypatch):
    origins,env,folder=live_demo
    for key,value in env.items():
        if key.endswith("_URL") or key in {"CONTROL_TOKEN","BUILD_VERSION"}: monkeypatch.setenv(key,value)
    # Dataclass defaults are evaluated on import, so replace cached settings explicitly.
    current=replace(settings(),gateway=origins["gateway"],order=origins["order"],payment=origins["payment"],inventory=origins["inventory"],proxy=origins["proxy"],proxy_control=origins["proxy_control"],control_token="integration-control")
    import app.experiments.runner as runner
    import app.verification.observer as observer
    monkeypatch.setattr(runner,"settings",lambda:current)
    monkeypatch.setattr(observer,"settings",lambda:current)
    return current
