"""Run actual browser checks plus a private read-only preview; existing app required."""
import os
from pathlib import Path
import shutil
import subprocess
import time
import httpx
from local import environment
ROOT=Path(__file__).resolve().parents[1]

def main():
    env=environment();ui=Path(env.get('FRONTEND_BUILD_DIR',str(ROOT/'frontend'))).resolve();node=shutil.which('node');logs=ROOT/'work/phase4';logs.mkdir(parents=True,exist_ok=True)
    with httpx.Client(trust_env=False,timeout=3) as client:
        for url in ['http://127.0.0.1:8000/ready','http://127.0.0.1:3000/']:
            try:client.get(url).raise_for_status()
            except httpx.HTTPError:raise SystemExit('Running local app is required. Start it and verify host readiness before browser acceptance.')
    standalone=ui/'.next/standalone';shutil.copytree(ui/'.next/static',standalone/'.next/static',dirs_exist_ok=True)
    with open(logs/'readonly-preview.log','w') as log:
        process=subprocess.Popen([node,str(standalone/'server.js')],cwd=ui,env={**env,'PORT':'3001','HOSTNAME':'127.0.0.1','ACCESS_MODE':'read_only','BACKEND_URL':'http://127.0.0.1:8000'},stdout=log,stderr=log)
        try:
            end=time.monotonic()+30
            with httpx.Client(trust_env=False,timeout=1) as client:
                while time.monotonic()<end:
                    try:
                        if client.get('http://127.0.0.1:3001/').status_code==200:break
                    except httpx.HTTPError:pass
                    if process.poll() is not None:raise RuntimeError('Read-only preview exited')
                    time.sleep(.2)
                else:raise TimeoutError('Read-only preview did not start')
            subprocess.run(['npm','run','test:e2e'],cwd=ROOT/'frontend',env={**env,'PLAYWRIGHT_BASE_URL':'http://127.0.0.1:3000','READONLY_BASE_URL':'http://127.0.0.1:3001','PLAYWRIGHT_CHANNEL':env.get('PLAYWRIGHT_CHANNEL','chrome')},check=True)
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
if __name__=='__main__':main()
