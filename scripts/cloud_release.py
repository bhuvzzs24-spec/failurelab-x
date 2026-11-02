"""Approved release helpers. URLs are exact operator configuration, not API input."""
import argparse
import os
import re
import time
from urllib.parse import urlsplit,parse_qs,urlencode,urlunsplit
import httpx

def public_origin(value):
    url=urlsplit(value)
    if url.scheme!='https' or not url.hostname or url.hostname in {'localhost','127.0.0.1','::1'} or url.hostname.endswith('.invalid') or url.username or url.password or url.path not in ('','/') or url.query or url.fragment:raise ValueError('An approved exact public HTTPS origin is required')
    return value.rstrip('/')

def release_hook(value,revision):
    url=urlsplit(value)
    if not re.fullmatch('[a-f0-9]{40}',revision) or url.scheme!='https' or url.hostname!='api.render.com' or not re.fullmatch(r'/deploy/srv-[a-z0-9]+',url.path) or url.username or url.password or url.fragment:raise ValueError('Invalid approved Render hook or revision')
    query=parse_qs(url.query)
    if not query.get('key') or set(query)-{'key','ref'}:raise ValueError('Render deploy hook must have its secret key')
    query['ref']=[revision]
    return urlunsplit((url.scheme,url.netloc,url.path,urlencode(query,doseq=True),''))

def deploy_backend(revision):
    if os.getenv('FAILURELAB_PUBLIC_RELEASE_APPROVED')!='true':raise ValueError('Public release is not approved')
    api=public_origin(os.environ['PUBLIC_BACKEND_ORIGIN'])
    hook=release_hook(os.environ['RENDER_DEPLOY_HOOK'],revision)
    with httpx.Client(trust_env=False,follow_redirects=False,timeout=10) as client:
        try:
            response=client.post(hook)
            if response.status_code not in (200,202):raise ValueError('Provider rejected deployment')
        except httpx.HTTPError:raise ValueError('Provider deployment request failed; inspect its private dashboard') from None
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            try:
                health=client.get(api+'/health');ready=client.get(api+'/ready')
                if health.status_code==200 and health.json().get('version')==revision and ready.status_code==200:
                    print('Backend is ready at the exact approved revision.');return
            except (httpx.HTTPError,ValueError):pass
            time.sleep(5)
    raise ValueError('Backend did not become ready at the approved revision; frontend was not released')

def smoke(frontend,*,expected_revision=None):
    frontend=public_origin(frontend)
    with httpx.Client(trust_env=False,follow_redirects=False,timeout=10) as client:
        for path in ('/','/graph','/experiments','/ai','/explorer','/replay','/verification','/evidence'):
            response=client.get(frontend+path)
            if response.status_code!=200 or 'FailureLab' not in response.text:raise ValueError('Public workspace page did not pass external HTTP smoke check')
        health=client.get(frontend+'/api/health')
        if health.status_code!=200 or health.json().get('status')!='ready':raise ValueError('Public frontend/backend health is not ready')
        session=client.get(frontend+'/api/backend/api/v1/session')
        access=session.json() if session.status_code==200 else {}
        if access.get('role')!='viewer' or not access.get('read_only') or access.get('can_execute') or access.get('can_manage'):raise ValueError('Public access is not viewer-only')
        if expected_revision:
            backend=client.get(frontend+'/api/backend/health')
            if backend.status_code!=200 or backend.json().get('version')!=expected_revision:raise ValueError('Public frontend is not connected to the approved backend revision')
        projects=client.get(frontend+'/api/backend/api/v1/projects')
        if projects.status_code!=200:raise ValueError('Public data API is unavailable')
        # Invalid input cannot create a row, even if a permission regression exists.
        denied=client.post(frontend+'/api/backend/api/v1/projects',headers={'Origin':frontend},json={})
        if denied.status_code!=403:raise ValueError('Public mutation boundary failed')
    print('External HTTPS workspace, API readiness, viewer role and read-only mutation checks passed.')

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    deploy=sub.add_parser('backend');deploy.add_argument('--revision',required=True)
    test=sub.add_parser('smoke');test.add_argument('--url',required=True);test.add_argument('--revision')
    args=parser.parse_args()
    try:
        if args.action=='backend':deploy_backend(args.revision)
        else:smoke(args.url,expected_revision=args.revision)
    except (ValueError,KeyError):raise SystemExit('Cloud release check failed. No success URL is claimed. Inspect approved configuration and provider dashboards.') from None
if __name__=='__main__':main()
