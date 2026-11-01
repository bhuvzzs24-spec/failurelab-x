"""Database outbox jobs, fenced ownership, bounded execution and immutable evidence."""
import asyncio
import hashlib
import json
import logging
import time
import uuid
from sqlalchemy import select, update
from app.core.db import SessionLocal
from app.models.entities import Project, Service, Dependency, Invariant, SandboxLease
from app.models.research import ResearchJob, ResearchTrial, ResearchFinding, ResearchDecision, RepairCandidate, ResearchArtifact
from app.schemas.research import ResearchCreate, Scenario
from app.benchmarks.executor import HTTPExecutor
from app.planning.search import search
from app.minimization.reduce import minimize
from app.causal.investigate import investigate
from app.repair.patches import prepare
from app.repair.client import verify_isolated
from app.providers.ollama import propose
TERMINAL={'COMPLETED','FAILED','CANCELLED'}
class Stopped(Exception): pass
class ResearchBusy(Exception): pass
class ResearchRunner:
    def __init__(self,sessions=SessionLocal,executor=None): self.sessions=sessions; self.executor=executor or HTTPExecutor()
    def artifact(self,job_id,kind,payload):
        data=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if len(data)>256*1024: raise ValueError('research artifact exceeds 256 KiB')
        with self.sessions.begin() as db:
            db.add(ResearchArtifact(job_id=job_id,kind=kind,payload=payload,sha256=hashlib.sha256(data).hexdigest()))
    def check(self,job_id,owner):
        with self.sessions() as db:
            job=db.get(ResearchJob,job_id)
            if job is None or job.owner!=owner or job.status!='RUNNING' or job.cancel_requested or job.deadline<=time.time(): raise Stopped('cancelled, deadline expired or ownership lost')
    async def run(self,job_id):
        owner=str(uuid.uuid4()); now=time.time()
        with self.sessions.begin() as db:
            job=db.get(ResearchJob,job_id)
            if not job or job.status not in ('CREATED','QUEUED'): return
            if job.cancel_requested or job.deadline<=now:
                job.status='CANCELLED' if job.cancel_requested else 'FAILED'; job.error='Stopped before execution'; job.updated_at=now; return
            lease=db.execute(update(SandboxLease).where(SandboxLease.id=='benchmark',SandboxLease.expires_at<now).values(run_id=job_id,expires_at=now+650)).rowcount
            if not lease: raise ResearchBusy()
            changed=db.execute(update(ResearchJob).where(ResearchJob.id==job_id,ResearchJob.status.in_(['CREATED','QUEUED'])).values(owner=owner,status='RUNNING',updated_at=now)).rowcount
            if not changed: raise ResearchBusy()
            config=ResearchCreate.model_validate(job.input); project=job.project_id; deadline=job.deadline
        async def execute(scenario,variant='original'):
            self.check(job_id,owner)
            scenario=Scenario.model_validate(scenario.model_dump())
            trial=await self.executor(scenario,variant)
            self.check(job_id,owner) # stale workers cannot publish outcomes
            encoded=json.dumps(trial['evidence'],allow_nan=False).encode()
            if len(encoded)>256*1024: raise ValueError('trial evidence exceeds size cap')
            with self.sessions.begin() as db:
                owned=db.execute(update(ResearchJob).where(ResearchJob.id==job_id,ResearchJob.owner==owner,ResearchJob.status=='RUNNING',ResearchJob.cancel_requested==0,ResearchJob.deadline>time.time()).values(updated_at=time.time())).rowcount
                if not owned: raise Stopped('ownership changed before evidence publication')
                db.add(ResearchTrial(job_id=job_id,project_id=project,**trial)); db.flush()
                if trial['classification']=='APPLICATION_VIOLATION':
                    finding=db.scalar(select(ResearchFinding).where(ResearchFinding.project_id==project,ResearchFinding.signature==trial['signature']))
                    if finding: finding.occurrences+=1
                    else: db.add(ResearchFinding(project_id=project,signature=trial['signature'],first_trial_id=trial['id'],summary=scenario.defect+': '+', '.join(trial['evidence'].get('violated_rules',[]))))
            return trial
        def record(step,scenario,score,context,reward,trial):
            self.check(job_id,owner)
            with self.sessions.begin() as db: db.add(ResearchDecision(job_id=job_id,step=step,scenario=scenario.model_dump(),context=context,score=score,reward=reward,cost_seconds=trial['cost_seconds']))
        status='COMPLETED'; result={}; error=None
        try:
            self.artifact(job_id,'lifecycle',{'status':'RUNNING','execution_id':job_id})
            result=await asyncio.wait_for(self.work(config,project,execute,record),timeout=max(.01,deadline-time.time()))
            self.check(job_id,owner)
            self.artifact(job_id,'report',result)
        except (Stopped,asyncio.TimeoutError) as exc:
            with self.sessions() as db: row=db.get(ResearchJob,job_id); cancelled=bool(row and row.cancel_requested)
            status='CANCELLED' if cancelled else 'FAILED'; error='Cancellation requested' if cancelled else 'Execution deadline or ownership expired'
        except Exception as exc:
            logging.getLogger('failurelab').exception('research job failed',extra={'job_id':job_id})
            status='FAILED'; error='Research execution failed: '+type(exc).__name__
        finally:
            with self.sessions.begin() as db:
                finished=db.execute(update(ResearchJob).where(ResearchJob.id==job_id,ResearchJob.owner==owner,ResearchJob.status=='RUNNING').values(status=status,result=result,error=error,updated_at=time.time())).rowcount
                # Faults are request-local, bounded <=500ms; reserve a drain period even on cancellation.
                if finished: db.execute(update(SandboxLease).where(SandboxLease.id=='benchmark',SandboxLease.run_id==job_id).values(expires_at=time.time()+2))
    async def work(self,config,project,execute,record):
        with self.sessions() as db:
            graph={'nodes':[{'id':r.id,'name':r.name} for r in db.scalars(select(Service).where(Service.project_id==project))],'edges':[{'source_id':r.source_id,'target_id':r.target_id} for r in db.scalars(select(Dependency).where(Dependency.project_id==project))]}
            invariants=[r.rule for r in db.scalars(select(Invariant).where(Invariant.project_id==project))]
            history=[{'scenario':r.scenario,'signature':r.signature,'cost_seconds':r.cost_seconds,'classification':r.classification} for r in db.scalars(select(ResearchTrial).where(ResearchTrial.project_id==project,ResearchTrial.variant=='original').order_by(ResearchTrial.created_at.desc()).limit(500))]
            source=db.get(ResearchTrial,config.source_trial_id) if config.source_trial_id else None
            scenario=Scenario.model_validate(source.scenario) if source else None
            signature=source.signature if source else None
        if config.kind=='SEARCH': return await search(config.search,execute,record,graph,invariants,history)
        if config.kind=='MINIMIZE': return (await minimize(scenario,signature,execute,config.budget,config.repeats)).model_dump()
        if config.kind=='INVESTIGATE':
            report=await investigate(scenario,signature,execute,config.budget,config.repeats)
            report['model_proposals']=await propose([source.id],{'scenario':source.scenario,'violated_rules':source.evidence.get('violated_rules',[])})
            return report
        if config.kind=='REPAIR':
            suggestions=await propose([source.id],{'defect':scenario.defect,'violated_rules':source.evidence.get('violated_rules',[])})
            defect=scenario.defect
            proposals=suggestions.get('proposals',[])
            # Validated model can suggest a policy, but cannot inject source or assert tests.
            selected=next((p['policy_defect'] for p in proposals if p.get('policy_defect')==defect),defect)
            patch,details=prepare(selected); details['model_proposals']=suggestions; details['runtime_sha256']=source.evidence.get('versions',{}).get('gateway',{}).get('runtime_sha256')
            with self.sessions.begin() as db:
                candidate=RepairCandidate(project_id=project,source_trial_id=source.id,patch=patch,details=details); db.add(candidate); db.flush(); identity=candidate.id
            return {'candidate_id':identity,'status':'PREPARED','checks':details['checks'],'scope':'Constrained policy repair; candidate execution requires isolated verification.'}
        if config.kind=='VERIFY':
            with self.sessions() as db:
                candidate=db.get(RepairCandidate,config.candidate_id); source=db.get(ResearchTrial,candidate.source_trial_id)
                result=await verify_isolated(candidate,Scenario.model_validate(source.scenario))
            with self.sessions.begin() as db:
                db.execute(update(RepairCandidate).where(RepairCandidate.id==config.candidate_id).values(status=result['outcome']))
            return result
        if config.kind=='BENCHMARK':
            results=[]
            for seed in config.seeds:
                for strategy in ('random','coverage','adaptive'):
                    selection=config.search.model_copy(update={'seed':seed,'strategy':strategy})
                    results.append(await search(selection,execute,record,graph,invariants,history=[]))
            references=[]
            from app.benchmarks.catalog import witness
            for defect in config.search.defects:
                case=witness(defect); original=await execute(case); repeated=await execute(case); reference=await execute(case,'reference'); baseline=await execute(case.model_copy(update={'actions':[],'concurrency':1}))
                references.append({'defect':defect,'original_trial_id':original['id'],'reference_trial_id':reference['id'],'original':original['classification'],'reference':reference['classification'],'repeat_trial_id':repeated['id'],'repeat_matches_signature':original['classification']=='APPLICATION_VIOLATION' and repeated['classification']=='APPLICATION_VIOLATION' and original['signature']==repeated['signature'],'baseline_trial_id':baseline['id'],'baseline':baseline['classification'],'reference_wall_delta_seconds':reference['cost_seconds']-original['cost_seconds']})
            means={s:sum(r['unique_bugs'] for r in results if r['strategy']==s)/len(config.seeds) for s in ('random','coverage','adaptive')}
            return {'comparisons':results,'mean_unique_bugs':means,'adaptive_improved_observed_mean':means['adaptive']>max(means['random'],means['coverage']),'reference_comparisons':references,'reference_comparison_note':'Trusted shipped reference policies; not execution or verification of generated candidate patches.','witness_reproduction_matches':sum(r['repeat_matches_signature'] for r in references),'witness_pairs':len(references),'unexpected_control_violations':sum(r[v]=='APPLICATION_VIOLATION' for r in references for v in ('baseline','reference')),'candidate_repair_verification_success':None,'candidate_repair_verification_note':'Reported by independent VERIFY jobs; reference policies are not generated candidate verification.','seeds':config.seeds,'budget_per_strategy_per_seed':config.search.budget,'limitations':['Small finite candidate space; no generalization claim.','False positives require external adjudication; not reported as zero.','Wall costs reflect this execution environment.']}
        raise ValueError('unsupported job')

def recover_research(sessions=SessionLocal):
    with sessions.begin() as db:
        jobs=list(db.scalars(select(ResearchJob).where(ResearchJob.status.notin_(TERMINAL),ResearchJob.deadline<time.time())))
        for job in jobs:
            job.status='CANCELLED' if job.cancel_requested else 'FAILED'; job.updated_at=time.time(); job.error='Deadline expired or worker lost; bounded request-local faults expire automatically. Partial trial evidence retained.'
