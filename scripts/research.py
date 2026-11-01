"""Public API client: durable research jobs and the complete bounded pipeline."""
import argparse
import json
import os
import time
import uuid
import httpx

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('kind',choices=['SEARCH','MINIMIZE','INVESTIGATE','REPAIR','VERIFY','BENCHMARK','PIPELINE']); parser.add_argument('--url',default='http://127.0.0.1:8000'); parser.add_argument('--project',required=True); parser.add_argument('--trial'); parser.add_argument('--candidate'); parser.add_argument('--budget',type=int,default=12); parser.add_argument('--strategy',choices=['random','coverage','adaptive'],default='adaptive'); parser.add_argument('--defect',default='payment_ack_loss'); args=parser.parse_args()
    with httpx.Client(base_url=args.url,headers={'Authorization':'Bearer '+os.getenv('API_TOKEN','local-development-token')},trust_env=False,timeout=15) as client:
        def call(method,path,body=None):
            response=client.request(method,'/api/v1/research/'+path,json=body); response.raise_for_status(); return response.json()
        def job(kind,trial=None,candidate=None):
            body={'kind':kind,'idempotency_key':uuid.uuid4().hex,'budget':max(2,args.budget),'source_trial_id':trial,'candidate_id':candidate,'search':{'strategy':args.strategy,'budget':args.budget,'defects':[args.defect]},'seeds':[17,42,93]}
            row=call('POST','projects/'+args.project+'/jobs',body); print(json.dumps({'job':row['id'],'kind':kind}),flush=True)
            deadline=time.monotonic()+650
            while row['status'] in ('CREATED','QUEUED','RUNNING') and time.monotonic()<deadline:
                time.sleep(1); row=call('GET','jobs/'+row['id'])
            print(json.dumps(row,indent=2),flush=True)
            if row['status']!='COMPLETED': raise RuntimeError('Job did not complete: '+str(row.get('error')))
            return row
        if args.kind!='PIPELINE': job(args.kind,args.trial,args.candidate); return
        searched=job('SEARCH')
        trials=call('GET','projects/'+args.project+'/trials?limit=100')['items']
        trial=next((t for t in trials if t['job_id']==searched['id'] and t['classification']=='APPLICATION_VIOLATION'),None)
        if trial is None: raise RuntimeError('No violation discovered within this budget; increase budget or inspect delivered injections.')
        job('MINIMIZE',trial['id']); job('INVESTIGATE',trial['id']); candidate=job('REPAIR',trial['id'])['result']['candidate_id']; job('VERIFY',candidate=candidate)
if __name__=='__main__': main()
