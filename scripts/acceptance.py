"""Real local acceptance workflow; writes bounded evidence, never fake successes."""
import argparse
import json
import os
from pathlib import Path
import time
import uuid
from urllib.parse import urlsplit
import httpx
from local import environment
from seed import seed

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8000');parser.add_argument('--benchmark',action='store_true');parser.add_argument('--budget',type=int,default=12);parser.add_argument('--output',type=Path,default=Path('work/phase4/acceptance.json'));args=parser.parse_args()
    parsed=urlsplit(args.url)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost') or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:raise SystemExit('Acceptance runner accepts only the managed local API origin')
    env=environment();os.environ['API_TOKEN']=env['API_TOKEN']
    registered=seed(args.url,False);project=registered['project_id'];record={'project_id':project,'api_origin':args.url,'stages':{},'limitations':['Generated candidates execute only in the restricted Docker agent.','A completed job is not necessarily a successful verification.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():
        fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as handle:json.dump(record,handle,indent=2)
    with httpx.Client(base_url=args.url,trust_env=False,timeout=15,headers={'Authorization':'Bearer '+env['API_TOKEN']}) as client:
        def call(method,path,body=None):
            response=client.request(method,'/api/v1'+path,json=body);response.raise_for_status();return response.json()
        def pages(path):
            items=[]
            for offset in range(0,100000,100):
                data=call('GET',path+('?offset=' if '?' not in path else '&offset=')+str(offset)+'&limit=100');items+=data['items']
                if len(items)>=data['total']:return items
            raise RuntimeError('Collection too large for local acceptance export')
        graph=call('GET',f'/projects/{project}/graph');assert len(graph['nodes'])==4 and len(graph['edges'])>=3
        run=call('POST',f"/experiments/{registered['experiment_id']}/runs",{'idempotency_key':uuid.uuid4().hex})
        end=time.monotonic()+120
        while run['status'] not in ('COMPLETED','FAILED','CANCELLED') and time.monotonic()<end:
            time.sleep(.5);run=call('GET','/runs/'+run['id'])
        summary=call('GET','/runs/'+run['id']+'/summary')
        assert run['status']=='COMPLETED' and summary['findings'],'Legacy fault did not produce a measured finding'
        baseline=next(a['payload'] for a in summary['artifacts'] if a['kind']=='snapshot' and a['payload'].get('stage')=='baseline')
        assert baseline['state']['order']['status']=='finalized' and baseline['state']['payment']['status']=='charged'
        record['stages']['normal_and_fault_workflows']=summary;save();print('Normal baseline and controlled fault: measured PASS then invariant violation',flush=True)
        def job(kind,source=None,candidate=None,budget=None):
            body={'kind':kind,'idempotency_key':uuid.uuid4().hex,'source_trial_id':source,'candidate_id':candidate,'budget':40 if kind=='MINIMIZE' else 20,'search':{'strategy':'adaptive','budget':budget or args.budget,'seed':42,'defects':['payment_ack_loss'] if kind!='BENCHMARK' else ['payment_ack_loss','unsafe_retry','lost_finalization','inventory_drift','concurrent_retry','failed_compensation']},'seeds':[17,42,93]}
            row=call('POST',f'/research/projects/{project}/jobs',body);end=time.monotonic()+650
            while row['status'] in ('CREATED','QUEUED','RUNNING') and time.monotonic()<end:
                time.sleep(.5);row=call('GET','/research/jobs/'+row['id'])
            record['stages'][kind]=row;save();print(kind,row['status'],row['result'].get('outcome',''),flush=True)
            if row['status']!='COMPLETED':raise RuntimeError(kind+' did not complete: '+str(row.get('error')))
            return row
        search=job('SEARCH');trials=pages('/research/jobs/'+search['id']+'/trials');source=next((t for t in trials if t['classification']=='APPLICATION_VIOLATION'),None)
        if source is None:raise RuntimeError('No violation discovered within this budget; no source failure was invented.')
        job('MINIMIZE',source['id']);job('INVESTIGATE',source['id']);repair=job('REPAIR',source['id']);verified=job('VERIFY',candidate=repair['result']['candidate_id'])
        record['verification_outcome']=verified['result']['outcome']
        record['verification_evidence_export']={'job':verified,'artifacts':pages('/research/jobs/'+verified['id']+'/artifacts'),'source_trial':source,'candidate':call('GET','/research/candidates/'+repair['result']['candidate_id'])}
        if args.benchmark:job('BENCHMARK')
        save()
        print('Acceptance evidence written. Docker unavailability is an infrastructure result, not a passing patch.',flush=True)
if __name__=='__main__':main()
