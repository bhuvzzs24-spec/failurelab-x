"""Static release safety checks. Does not call providers or publish anything."""
import json
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]

def validate():
    blueprint=yaml.safe_load((ROOT/'infrastructure/cloud/render.yaml').read_text())
    services=blueprint['services'];assert {s['type'] for s in services}=={'web','keyvalue'},'Public blueprint must not include execution workers'
    api=next(s for s in services if s['type']=='web');limits=next(s for s in services if s['type']=='keyvalue')
    env={item['key']:item for item in api['envVars']}
    assert api['runtime']=='docker' and api['autoDeployTrigger']=='off' and api['healthCheckPath']=='/ready'
    assert env['APP_MODE']['value']=='read_only' and env['DEPLOYMENT_ENV']['value']=='cloud_read_only'
    assert env['READONLY_DATABASE_ENFORCED']['value']=='1' and env['DATABASE_URL']['sync'] is False
    assert env['AUTH_VIEWER_TOKEN']['sync'] is False
    assert not {'AUTH_ADMIN_TOKEN','AUTH_OPERATOR_TOKEN','CONTROL_TOKEN','REPAIR_AGENT_TOKEN','CLOUD_MIGRATION_DATABASE_URL'}&env.keys()
    assert limits['ipAllowList']==[] and blueprint['databases'][0]['ipAllowList']==[]
    assert blueprint['databases'][0]['databaseName']=='failurelab_public'
    vercel=json.loads((ROOT/'frontend/vercel.json').read_text());assert vercel['git']['deploymentEnabled'] is False
    release=(ROOT/'.github/workflows/cloud-release.yml').read_text()
    for required in ("vars.FAILURELAB_PUBLIC_RELEASE_APPROVED == 'true'","github.event.workflow_run.conclusion == 'success'",'failurelab-cloud-release','secrets.CLOUD_MIGRATION_DATABASE_URL','--revision "$EXPECTED_REVISION"','--prebuilt --prod','public-read-only'):
        assert required in release,required
    client=(ROOT/'frontend/src/lib/api.ts').read_text()
    assert 'fetch(`/api/backend/${path}`' in client and 'localhost' not in client and 'NEXT_PUBLIC_' not in client
    print('Static cloud boundaries passed: readonly API, private persistence, no workers, gated release, same-origin client.')
if __name__=='__main__':validate()
