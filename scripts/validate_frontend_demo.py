"""Offline preview-profile checks. Never requires evidence or deploys resources."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def validate():
    config=json.loads((ROOT/'frontend/vercel.demo.json').read_text())
    assert config['git']['deploymentEnabled'] is False
    assert config['framework']=='nextjs'
    assert config['buildCommand']=='node scripts/check-demo.mjs && npm run build'
    assert not {'env','build','builds','rewrites','crons'}&config.keys(),'Do not use deprecated environment fields or add external/execution services'
    profile=(ROOT/'infrastructure/cloud/frontend-demo.env.example').read_text()
    values=dict(line.split('=',1) for line in profile.splitlines() if line and not line.startswith('#'))
    assert values=={'DATA_MODE':'recorded_demo','DEPLOYMENT_ENV':'frontend_demo','ACCESS_MODE':'read_only'}
    assert 'frontend/demo-data/' in (ROOT/'.gitignore').read_text()
    assert 'frontend/demo-data/' in (ROOT/'.dockerignore').read_text()
    assert 'demo-data/' in (ROOT/'frontend/.dockerignore').read_text()
    adapter=(ROOT/'frontend/src/lib/recorded-demo.ts').read_text()
    assert all(forbidden not in adapter for forbidden in ('fetch(', 'child_process', 'node:net', 'eval(', 'http://'))
    assert 'env.VERCEL_ENV !== "preview"' in adapter
    bridge=(ROOT/'frontend/src/lib/bridge.ts').read_text()
    assert bridge.index('return recordedBridge(')<bridge.index('await fetch(')
    assert 'new URL(env.BACKEND_URL ?? "")' in bridge,'No implicit localhost API fallback'
    print('Frontend-only Preview configuration passed: no connections, no credentials, private evidence, no auto-deploy or production target.')
if __name__=='__main__':validate()
