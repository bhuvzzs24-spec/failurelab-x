"""Real browser acceptance. Preview mode serves a separate build over the live local API."""
import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import httpx
from local import environment
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true',help='Serve the selected build on 3002 while preserving the existing UI');args=parser.parse_args()
    env=environment();ui=Path(env.get('FRONTEND_BUILD_DIR',str(ROOT/'frontend'))).resolve();node=shutil.which('node');logs=ROOT/'work/redesign-browser';logs.mkdir(parents=True,exist_ok=True)
    if not node or not (ui/'.next/standalone/server.js').exists():raise SystemExit('A production standalone build and Node are required')
    primary=3002 if args.preview else 3000;readonly=3003 if args.preview else 3001
    with httpx.Client(trust_env=False,timeout=3) as client:
        required=['http://127.0.0.1:8000/ready']+([] if args.preview else ['http://127.0.0.1:3000/'])
        for url in required:
            try:client.get(url).raise_for_status()
            except httpx.HTTPError:raise SystemExit('Running local API/app required. Verify host readiness before browser acceptance.')
    for port in [readonly]+([primary] if args.preview else []):
        with socket.socket() as sock:
            try:sock.bind(('127.0.0.1',port))
            except OSError:raise SystemExit('Preview port is occupied; no process was stopped')
    standalone=ui/'.next/standalone';shutil.copytree(ui/'.next/static',standalone/'.next/static',dirs_exist_ok=True)
    processes=[];handles=[]
    try:
        for port,mode in ([(primary,'local')] if args.preview else [])+[(readonly,'read_only')]:
            log=open(logs/f'preview-{port}.log','w');handles.append(log)
            process=subprocess.Popen([node,str(standalone/'server.js')],cwd=ui,env={**env,'PORT':str(port),'HOSTNAME':'127.0.0.1','ACCESS_MODE':mode,'DEPLOYMENT_ENV':'local','VERCEL':'0','BACKEND_URL':'http://127.0.0.1:8000'},stdout=log,stderr=log);processes.append(process)
            end=time.monotonic()+30
            with httpx.Client(trust_env=False,timeout=1) as client:
                while time.monotonic()<end:
                    try:
                        if client.get(f'http://127.0.0.1:{port}/api/health').status_code==200:break
                    except httpx.HTTPError:pass
                    if process.poll() is not None:raise RuntimeError('Owned preview exited')
                    time.sleep(.2)
                else:raise TimeoutError('Owned preview did not become ready')
        subprocess.run(['npm','run','test:e2e'],cwd=ROOT/'frontend',env={**env,'PLAYWRIGHT_BASE_URL':f'http://127.0.0.1:{primary}','READONLY_BASE_URL':f'http://127.0.0.1:{readonly}','PLAYWRIGHT_CHANNEL':env.get('PLAYWRIGHT_CHANNEL','chrome')},check=True)
    finally:
        for process in reversed(processes):
            if process.poll() is None:process.terminate()
        for process in reversed(processes):
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        for log in handles:log.close()
if __name__=='__main__':main()
