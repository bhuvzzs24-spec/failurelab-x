"""Local Compose lifecycle. Host probes are real; no infrastructure fallback success."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
import json
import urllib.request
import urllib.error
ROOT=Path(__file__).resolve().parents[1]
def command(args,**kwargs):return subprocess.run(args,cwd=ROOT,check=True,**kwargs)
def initialize_env():
    path=ROOT/'.env'
    if path.exists():return
    values={k:secrets.token_urlsafe(32) for k in ('API_TOKEN','CONTROL_TOKEN','POSTGRES_PASSWORD','DEMO_POSTGRES_PASSWORD','REPAIR_AGENT_TOKEN')}
    values.update(BUILD_VERSION='phase4-local',APP_MODE='local',REPAIR_AGENT_URL='',OLLAMA_URL='')
    try:
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(descriptor,'w') as handle:handle.write(''.join(k+'='+v+'\n' for k,v in values.items()))
        print('Created .env with local credentials; values were not printed.')
    except FileExistsError:pass

def probe(url):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        with opener.open(url,timeout=2) as response:
            if response.status!=200:return False
            if url.endswith('/ready'):return json.loads(response.read(65536)).get('status')=='ready'
            return b'FailureLab' in response.read(262144)
    except (urllib.error.URLError,ValueError,TimeoutError,OSError):return False

def docker_socket_group():return os.stat('/var/run/docker.sock').st_gid

def compose_args():
    value=os.getenv('REPAIR_AGENT_URL')
    if value is None and (ROOT/'.env').exists():
        value=next((line.split('=',1)[1].strip().strip('"').strip("'") for line in (ROOT/'.env').read_text().splitlines() if line.startswith('REPAIR_AGENT_URL=')),'')
    return ['docker','compose']+(['--profile','verification'] if value=='http://repair-agent:8110' else [])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['start','stop','restart','status','logs','verifier']);args=parser.parse_args()
    if not shutil.which('docker'):raise SystemExit('Docker CLI is unavailable. Install/start Docker Desktop, then retry. No Compose service or localhost URL was verified.')
    result=subprocess.run(['docker','info','--format','{{.ServerVersion}}'],capture_output=True,cwd=ROOT)
    if result.returncode:raise SystemExit('Docker daemon is unavailable. Start Docker Desktop and retry.')
    command(['docker','compose','version'],stdout=subprocess.DEVNULL)
    if args.action=='verifier':
        initialize_env()
        if os.getuid()==0:raise SystemExit('Enable the local verifier using an unprivileged host account.')
        inputs=(ROOT/'work/agent-inputs').resolve()
        if ',' in str(inputs):raise SystemExit('Verifier input path must not contain commas')
        inputs.mkdir(parents=True,exist_ok=True,mode=0o700)
        path=ROOT/'.env';lines=path.read_text().splitlines();current={line.split('=',1)[0]:line.split('=',1)[1] for line in lines if '=' in line and not line.startswith('#')}
        token=current.get('REPAIR_AGENT_TOKEN','') or secrets.token_urlsafe(32)
        if len(token)<32:raise SystemExit('REPAIR_AGENT_TOKEN must be at least 32 characters; update it before enabling the verifier.')
        changes={'REPAIR_AGENT_TOKEN':token,'REPAIR_AGENT_URL':'http://repair-agent:8110','REPAIR_HOST_INPUT_ROOT':str(inputs),'LOCAL_UID':str(os.getuid()),'LOCAL_GID':str(os.getgid()),'DOCKER_GID':str(docker_socket_group())}
        lines=[line for line in lines if line.split('=',1)[0] not in changes]
        path.write_text('\n'.join(lines)+'\n'+''.join(k+'='+v+'\n' for k,v in changes.items()));path.chmod(0o600)
        command(['docker','build','-f','infrastructure/Dockerfile.verifier','-t','failurelab-verifier:phase3','.'])
        command(['docker','compose','--profile','verification','up','--build','-d','repair-agent','worker','api'])
        print('Private verifier configured. No agent port is published; inspect its health before verification. Docker access exists only in this trusted agent.')
    elif args.action in ('start','restart'):
        initialize_env();compose=compose_args();command(compose+['config','--quiet'])
        if args.action=='restart':command(['docker','compose','--profile','*','down']) # preserves volumes; migration/seed run on every start
        command(compose+['up','--build','-d'])
        urls=['http://127.0.0.1:8000/ready','http://127.0.0.1:3000/api/backend/ready','http://127.0.0.1:3000/']
        deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            if all(probe(url) for url in urls):break
            time.sleep(1)
        else:raise SystemExit('Host connectivity did not become ready. Run make status and make logs. Services may still be starting; no URL is claimed working.')
        command(compose+['exec','-T','api','python','scripts/seed.py','--register-only'])
        print('Host probes passed. Frontend: http://127.0.0.1:3000 · API: http://127.0.0.1:8000')
        print('Localhost works only while the required local services are running. make stop preserves database volumes.')
    elif args.action=='stop':command(['docker','compose','--profile','*','down'])
    elif args.action=='logs':command(['docker','compose','--profile','*','logs','--follow','--tail','100'])
    else:
        command(['docker','compose','--profile','*','ps','-a'])
        for label,url in [('Frontend','http://127.0.0.1:3000/'),('API readiness','http://127.0.0.1:8000/ready')]:print(label+': '+('reachable' if probe(url) else 'unreachable'))
if __name__=='__main__':main()
