"""Owned native Mac/Linux supervisor. Optional fallback when Docker is unavailable.

No untrusted candidate executes here. The restricted Docker verifier remains separate.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'work/native-services'

def environment():
    env=os.environ.copy();path=ROOT/'.env'
    if path.exists():
        for line in path.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line:continue
            key,value=line.split('=',1);value=value.strip()
            if value[:1] in ('"',"'") and value[-1:]==value[:1]:value=value[1:-1]
            if key.strip() in {'API_TOKEN','CONTROL_TOKEN','APP_MODE','OLLAMA_URL','OLLAMA_MODEL','REPAIR_AGENT_URL','REPAIR_AGENT_TOKEN'}:env.setdefault(key.strip(),value)
    if env.get('APP_MODE','local')!='local':raise SystemExit('Native sandbox launcher requires APP_MODE=local. Hosted read-only operation uses the deployment template.')
    env.setdefault('API_TOKEN','local-development-token');env.setdefault('CONTROL_TOKEN','local-control-token')
    return env

def read_owner():
    path=STATE/'owner.json'
    if not path.exists():return None
    row=json.loads(path.read_text())
    result=subprocess.run(['ps','-p',str(row['pid']),'-o','command='],capture_output=True,text=True)
    if result.returncode or str(Path(__file__).resolve()) not in result.stdout or row['instance'] not in result.stdout:return None
    return row

def supervise(instance):
    STATE.mkdir(parents=True,exist_ok=True);env=environment();processes=[];handles=[]
    def stop(signum,frame):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    def spawn(name,args,cwd):
        h=open(STATE/(name+'.log'),'a');handles.append(h)
        p=subprocess.Popen(args,cwd=cwd,env=env,stdout=h,stderr=h);processes.append(p);return p
    try:
        env['BACKEND_URL']='http://127.0.0.1:8000';env['HOSTNAME']='127.0.0.1';env['PORT']='3000'
        backend=spawn('backend',[sys.executable,'scripts/dev_stack.py','--state-dir',str(STATE/'data')],ROOT)
        ui=Path(env.get('FRONTEND_BUILD_DIR',str(ROOT/'frontend'))).resolve()
        node=shutil.which('node')
        frontend=spawn('frontend',[node,str(ui/'.next/standalone/server.js')],ui)
        import httpx
        end=time.monotonic()+180
        with httpx.Client(trust_env=False,timeout=2,headers={'Authorization':'Bearer '+env['API_TOKEN']}) as client:
            while time.monotonic()<end:
                if backend.poll() is not None or frontend.poll() is not None:raise RuntimeError('Owned service exited; inspect work/native-services logs')
                try:
                    ready=client.get('http://127.0.0.1:8000/ready')
                    page=client.get('http://127.0.0.1:3000/')
                    projects=client.get('http://127.0.0.1:8000/api/v1/projects')
                    if ready.status_code==200 and page.status_code==200 and 'FailureLab' in page.text and projects.status_code==200 and projects.json()['total']:
                        (STATE/'ready').write_text(instance);break
                except (httpx.HTTPError,ValueError,KeyError):pass
                time.sleep(.5)
            else:raise TimeoutError('Native startup timed out')
        while True:
            if any(p.poll() is not None for p in processes):raise RuntimeError('Owned service exited')
            time.sleep(.5)
    except KeyboardInterrupt:pass
    finally:
        (STATE/'ready').unlink(missing_ok=True)
        for p in reversed(processes):
            if p.poll() is None:p.terminate()
        for p in reversed(processes):
            try:p.wait(timeout=20)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        for h in handles:h.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','stop','status','supervise']);parser.add_argument('--instance');args=parser.parse_args()
    if args.action=='supervise':supervise(args.instance);return
    STATE.mkdir(parents=True,exist_ok=True);owner=read_owner()
    if args.action=='stop':
        if owner:
            os.kill(owner['pid'],signal.SIGTERM)
            deadline=time.monotonic()+60
            while read_owner():
                if time.monotonic()>deadline:raise SystemExit('Owned supervisor is still stopping. Inspect native logs before restarting; no unrelated process was stopped.')
                time.sleep(.2)
            print('Owned native stack stopped; database files are preserved.')
        else:print('No matching owned native supervisor is running; no process was stopped.')
        return
    if args.action=='status':print('Native supervisor '+('running; readiness '+str((STATE/'ready').exists()) if owner else 'stopped'));return
    if owner:
        ready=(STATE/'ready').exists() and (STATE/'ready').read_text()==owner['instance']
        print('Owned native supervisor already running. '+('Readiness recorded. Frontend: http://127.0.0.1:3000' if ready else 'Startup is not ready; inspect native logs.'))
        return
    env=environment();node=shutil.which('node')
    if not node or int(subprocess.check_output([node,'-p','process.versions.node.split(".")[0]']).decode())<24:raise SystemExit('Node 24+ is required in PATH')
    ui=Path(env.get('FRONTEND_BUILD_DIR',str(ROOT/'frontend'))).resolve();server=ui/'.next/standalone/server.js'
    if not server.exists():raise SystemExit('Production standalone build is missing. Run npm ci && npm run build in frontend first.')
    shutil.copytree(ui/'.next/static',server.parent/'.next/static',dirs_exist_ok=True)
    if not shutil.which('redis-server'):raise SystemExit('redis-server is required')
    # Refuse occupied ports; never stop an unrelated process to make room.
    for port in [3000,8000,16379,*range(18080,18086),*range(18090,18094)]:
        with socket.socket() as sock:
            try:sock.bind(('127.0.0.1',port))
            except OSError:raise SystemExit('Required local port '+str(port)+' is occupied; no process was stopped.')
    instance=uuid.uuid4().hex;log=open(STATE/'supervisor.log','a')
    process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'supervise','--instance',instance],cwd=ROOT,env=env,stdout=log,stderr=log,start_new_session=True);log.close()
    path=STATE/'owner.json';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as handle:json.dump({'pid':process.pid,'instance':instance},handle)
    deadline=time.monotonic()+190
    while time.monotonic()<deadline:
        if (STATE/'ready').exists() and (STATE/'ready').read_text()==instance:
            print('Native host probes passed. Frontend: http://127.0.0.1:3000 · API: http://127.0.0.1:8000');return
        if process.poll() is not None:raise SystemExit('Native supervisor exited. Inspect work/native-services/supervisor.log and service logs.')
        time.sleep(.5)
    os.kill(process.pid,signal.SIGTERM);raise SystemExit('Native startup timed out; owned shutdown requested.')
if __name__=='__main__':main()
