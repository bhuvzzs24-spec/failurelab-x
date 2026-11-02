"""Own two isolated preview servers. Both have outgoing sockets disabled.

Only tests a local production build; never creates a Vercel deployment.
"""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import httpx
ROOT=Path(__file__).resolve().parents[1]

def main():
    ui=Path(os.environ.get('FRONTEND_BUILD_DIR',str(ROOT/'frontend'))).resolve()
    standalone=ui/'.next/standalone';server=standalone/'server.js'
    if not server.exists():raise SystemExit('Build the frontend-only production demo first')
    for port in (3004,3005):
        with socket.socket() as sock:
            try:sock.bind(('127.0.0.1',port))
            except OSError:raise SystemExit('Demo test port occupied; no unrelated process was stopped')
    folder=ROOT/'work/demo-browser';folder.mkdir(parents=True,exist_ok=True)
    deny=folder/'deny-outbound.cjs';deny.write_text("require('node:net').Socket.prototype.connect=function(){throw new Error('Outbound networking forbidden in frontend-only demo acceptance')};\n")
    shutil.copytree(ui/'.next/static',standalone/'.next/static',dirs_exist_ok=True)
    missing=folder/'missing-instance'
    # A physically separate standalone copy lacks the dataset. No live instance's
    # evidence or source is renamed/modified to manufacture the error state.
    shutil.copytree(standalone,missing,dirs_exist_ok=True,ignore=shutil.ignore_patterns('demo-data'))
    env={k:v for k,v in os.environ.items() if k not in {'BACKEND_URL','HOSTED_BACKEND_ORIGIN','API_TOKEN','CONTROL_TOKEN','VERCEL_TOKEN','GH_TOKEN','GITHUB_TOKEN','DATABASE_URL','REDIS_URL','REPAIR_AGENT_URL','REPAIR_AGENT_TOKEN','OLLAMA_URL','OLLAMA_MODEL'} and not k.startswith('AUTH_')}
    env.update(DATA_MODE='recorded_demo',DEPLOYMENT_ENV='frontend_demo',ACCESS_MODE='read_only',HOSTNAME='127.0.0.1',NEXT_TELEMETRY_DISABLED='1',NODE_OPTIONS='--require '+str(deny))
    processes=[];handles=[]
    try:
        for port,entry in ((3004,server),(3005,missing/'server.js')):
            log=open(folder/f'{port}.log','w');handles.append(log)
            process=subprocess.Popen([shutil.which('node'),str(entry)],cwd=entry.parent,env={**env,'PORT':str(port)},stdout=log,stderr=log);processes.append(process)
            deadline=time.monotonic()+30
            with httpx.Client(trust_env=False,timeout=2) as client:
                while time.monotonic()<deadline:
                    try:
                        result=client.get(f'http://127.0.0.1:{port}/api/health')
                        if result.status_code==(200 if port==3004 else 503):break
                    except httpx.HTTPError:pass
                    if process.poll() is not None:raise RuntimeError('Owned demo server exited')
                    time.sleep(.2)
                else:raise TimeoutError('Recorded demo readiness did not match its evidence state')
        browser_env={k:v for k,v in env.items() if k!='NODE_OPTIONS'}
        subprocess.run(['npm','exec','--','playwright','test','--config','playwright.demo.config.ts'],cwd=ROOT/'frontend',env={**browser_env,'DEMO_BASE_URL':'http://127.0.0.1:3004','DEMO_MISSING_URL':'http://127.0.0.1:3005'},check=True)
    finally:
        for process in processes:
            if process.poll() is None:process.terminate()
        for process in processes:
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        for log in handles:log.close()
if __name__=='__main__':main()
