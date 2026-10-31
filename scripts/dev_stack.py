"""Local integration stack with real processes and SQLite; no Docker required.
Development/testing only. Compose remains the PostgreSQL production-oriented path.
"""
import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port",type=int,default=8000)
    parser.add_argument("--redis-port",type=int,default=16379)
    parser.add_argument("--base-port",type=int,default=18080)
    args=parser.parse_args()
    if not shutil.which("redis-server"): raise SystemExit("redis-server is required; install Redis or use Docker Compose")
    folder=ROOT/"work/local-stack"; folder.mkdir(parents=True,exist_ok=True)
    redis_folder=folder/"redis"; redis_folder.mkdir(exist_ok=True)
    env=os.environ.copy(); env["PYTHONPATH"]=str(ROOT/"backend")
    env["DATABASE_URL"]="sqlite:///"+str(folder/"platform.db")
    env["REDIS_URL"]=f"redis://127.0.0.1:{args.redis_port}/0"
    env["CELERY_QUEUE"]="failurelab-local"
    env.setdefault("API_TOKEN","local-development-token")
    env.setdefault("CONTROL_TOKEN","local-control-token")
    env["BUILD_VERSION"]="phase2-local-source"
    names=("gateway","order","payment","inventory","proxy","proxy_control")
    ports={name:args.base_port+index for index,name in enumerate(names)}
    for name,port in ports.items(): env[name.upper()+"_URL"]=f"http://127.0.0.1:{port}"
    env["BIND_HOST"]="127.0.0.1"
    env["DATA_PORT"]=str(ports["proxy"]); env["CONTROL_PORT"]=str(ports["proxy_control"])
    processes=[]; files=[]
    def spawn(name,command,extra=None):
        handle=(folder/(name+".log")).open("a"); files.append(handle)
        process=subprocess.Popen(command,cwd=ROOT,env={**env,**(extra or {})},stdout=handle,stderr=handle)
        processes.append((name,process)); return process
    def wait_http(url,process):
        deadline=time.monotonic()+60
        with httpx.Client(trust_env=False,timeout=.5) as client:
            while time.monotonic()<deadline:
                try:
                    if client.get(url).is_success: return
                except httpx.HTTPError: pass
                if process.poll() is not None: raise RuntimeError("A service exited; inspect work/local-stack logs")
                time.sleep(.1)
        raise TimeoutError("Service did not become ready: "+url)
    def stop(signum,frame): raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,stop)
    try:
        subprocess.run([sys.executable,"-m","alembic","upgrade","head"],cwd=ROOT,env=env,check=True)
        redis_process=spawn("redis",["redis-server","--bind","127.0.0.1","--port",str(args.redis_port),"--appendonly","yes","--dir",str(redis_folder)])
        import redis
        connection=redis.Redis.from_url(env["REDIS_URL"],socket_connect_timeout=.5)
        deadline=time.monotonic()+10
        while True:
            try:
                if connection.ping(): break
            except redis.ConnectionError: pass
            if time.monotonic()>deadline: raise TimeoutError("Local Redis did not start")
            time.sleep(.1)
        connection.close()
        for role in ("order","inventory","payment","proxy","gateway"):
            if role=="proxy": command=[sys.executable,"-m","app.faults.proxy"]
            else: command=[sys.executable,"-m","uvicorn","app.services.demo:create_app","--factory","--host","127.0.0.1","--port",str(ports[role]),"--no-access-log"]
            process=spawn(role,command,{"DEMO_ROLE":role,"DEMO_DATABASE_URL":"sqlite:///"+str(folder/(role+".db"))})
            wait_http(env["PROXY_CONTROL_URL" if role=="proxy" else role.upper()+"_URL"]+"/health",process)
        api=spawn("api",[sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port",str(args.api_port),"--no-access-log"])
        api_origin=f"http://127.0.0.1:{args.api_port}"; wait_http(api_origin+"/ready",api)
        spawn("worker",[sys.executable,"-m","celery","-A","app.workers.tasks.celery","worker","--pool=solo","--loglevel=INFO","--without-gossip","--without-mingle"])
        spawn("scheduler",[sys.executable,"-m","celery","-A","app.workers.tasks.celery","beat","--loglevel=INFO","--schedule",str(folder/"celerybeat")])
        subprocess.run([sys.executable,"scripts/seed.py","--url",api_origin,"--register-only"],cwd=ROOT,env=env,check=True)
        print(f"Local stack ready at {api_origin}. Real SQLite state, fake payments, local targets. Logs: work/local-stack/",flush=True)
        print("Development worker uses solo pool; Linux prefork hard time limits must be checked with Compose.",flush=True)
        while True:
            for name,process in processes:
                if process.poll() is not None: raise RuntimeError(name+" exited unexpectedly")
            time.sleep(.5)
    except KeyboardInterrupt: print("Stopping owned local processes",flush=True)
    finally:
        for _,process in reversed(processes):
            if process.poll() is None: process.terminate()
        for _,process in reversed(processes):
            try: process.wait(timeout=7)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        for handle in files: handle.close()
if __name__=="__main__": main()
