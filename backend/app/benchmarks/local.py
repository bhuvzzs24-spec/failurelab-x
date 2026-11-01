"""Trusted benchmark launcher shared by integration tests and isolated verifier."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from contextlib import contextmanager
import httpx

def port():
    with socket.socket() as sock: sock.bind(('127.0.0.1',0)); return sock.getsockname()[1]
@contextmanager
def cluster(folder,extra_env=None,package_root=None):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    urls={role:'http://127.0.0.1:'+str(port()) for role in ('gateway','order','payment','inventory')}
    env=os.environ.copy(); env.update(extra_env or {}); env.update({'BENCH_'+r.upper()+'_URL':u for r,u in urls.items()})
    # Resolve children from this imported package, not a stale editable install.
    if package_root is None:
        env['PYTHONPATH']=str(Path(__file__).resolve().parents[2])
    env['CONTROL_TOKEN']='isolated-benchmark-control'
    processes=[]; handles=[]
    try:
        for role,url in urls.items():
            local=env.copy(); local.update(BENCH_ROLE=role,BENCH_DATABASE_URL='sqlite:///'+str((folder/(role+'.db')).resolve()))
            handle=open(folder/(role+'.log'),'w'); handles.append(handle)
            command=[sys.executable,'-m','uvicorn','app.benchmarks.runtime:create_app','--factory','--host','127.0.0.1','--port',url.rsplit(':',1)[1],'--no-access-log','--log-level','error']
            processes.append(subprocess.Popen(command,env=local,cwd=package_root,stdout=handle,stderr=handle))
            deadline=time.monotonic()+20
            while True:
                try:
                    with httpx.Client(trust_env=False,timeout=.2) as client:
                        if client.get(url+'/health',headers={'X-Control-Token':env['CONTROL_TOKEN']}).status_code==200: break
                except httpx.HTTPError: pass
                if processes[-1].poll() is not None or time.monotonic()>deadline: raise RuntimeError('benchmark '+role+' startup failed: '+(folder/(role+'.log')).read_text()[-1500:])
                time.sleep(.05)
        yield urls,env['CONTROL_TOKEN']
    finally:
        for process in processes: process.terminate()
        for process in processes:
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        for handle in handles: handle.close()
