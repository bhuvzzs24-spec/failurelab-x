import asyncio
import time
import uuid
import platform
import httpx
from sqlalchemy import select, update
from pydantic import TypeAdapter
from opentelemetry import trace
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.entities import Run, Experiment, Invariant, Finding, SandboxLease
from app.schemas.contracts import ExperimentConfig, Rule
from app.repositories.evidence import artifact
from app.verification.observer import Observer
from app.invariants.engine import evaluate

TASK_HARD_LIMIT_SECONDS=130
SANDBOX_CRASH_HOLD_SECONDS=TASK_HARD_LIMIT_SECONDS+30+5
TERMINAL={"COMPLETED","FAILED","CANCELLED"}
class Busy(Exception): pass
class Cancelled(Exception): pass
class Deadline(Exception): pass

class Runner:
    def __init__(self,sessions=SessionLocal): self.sessions=sessions
    def event(self,run_id,kind,payload):
        with self.sessions() as db: return artifact(db,run_id,kind,payload).id
    def status(self,run_id,owner,status,result=None):
        with self.sessions.begin() as db:
            values={"status":status,"updated_at":time.time()}
            if result is not None: values["result"]=result
            changed=db.execute(update(Run).where(Run.id==run_id,Run.owner==owner,Run.status.not_in(TERMINAL)).values(**values)).rowcount
        if changed: self.event(run_id,"lifecycle",{"status":status})
    def claim(self,run_id):
        now=time.time(); owner=str(uuid.uuid4())
        with self.sessions.begin() as db:
            row=db.get(Run,run_id)
            if not row or row.status not in {"CREATED","QUEUED"}: return None
            if row.cancel_requested or row.deadline<=now:
                row.status="CANCELLED" if row.cancel_requested else "FAILED"
                row.result={"reason":"cancelled before execution" if row.cancel_requested else "queue deadline exceeded"}
                return None
            lock=db.execute(update(SandboxLease).where(SandboxLease.id==settings().sandbox,SandboxLease.expires_at<=now).values(run_id=run_id,expires_at=now+SANDBOX_CRASH_HOLD_SECONDS)).rowcount
            if not lock: raise Busy("sandbox is leased")
            claimed=db.execute(update(Run).where(Run.id==run_id,Run.status.in_(["CREATED","QUEUED"])).values(status="RUNNING",owner=owner,lease_until=now+SANDBOX_CRASH_HOLD_SECONDS,updated_at=now)).rowcount
            if not claimed: raise Busy("run already claimed")
            config=row.config; deadline=row.deadline
            project_id=db.get(Experiment,row.experiment_id).project_id
            rules={i.id:i.rule for i in db.scalars(select(Invariant).where(Invariant.project_id==project_id,Invariant.id.in_(config["invariant_ids"])))}
        self.event(run_id,"lifecycle",{"status":"RUNNING","owner":owner})
        return owner,config,deadline,rules
    async def monitor(self,run_id,owner):
        while True:
            with self.sessions() as db:
                row=db.get(Run,run_id)
                if row.cancel_requested: raise Cancelled()
                if row.owner!=owner or row.status in TERMINAL: raise Cancelled()
                if time.time()>=row.deadline: raise Deadline()
            await asyncio.sleep(.1)
    async def run(self,run_id):
        claim=self.claim(run_id)
        if claim is None: return
        owner,raw,deadline,rules=claim
        cfg=ExperimentConfig.model_validate(raw)
        headers={"X-Control-Token":settings().control_token,"X-Execution-ID":run_id,
                 "traceparent":f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"}
        result={}; final="FAILED"; cleaned=False
        async with httpx.AsyncClient(headers=headers,timeout=4,trust_env=False,follow_redirects=False) as client:
            work=asyncio.create_task(self.execute(client,run_id,owner,cfg,rules))
            monitor=asyncio.create_task(self.monitor(run_id,owner))
            try:
                done,_=await asyncio.wait({work,monitor},return_when=asyncio.FIRST_COMPLETED)
                if monitor in done: await monitor
                result=await work; final="COMPLETED"
            except Cancelled: final="CANCELLED"; result={"reason":"cancellation requested"}
            except Deadline: result={"reason":"experiment deadline exceeded"}
            except Exception as exc: result={"reason":type(exc).__name__,"detail":str(exc)[:500]}
            finally:
                for task in (work,monitor):
                    task.cancel()
                    try: await task
                    except (asyncio.CancelledError,Exception): pass
                try:
                    response=await client.delete(settings().proxy_control+"/lease/"+run_id)
                    response.raise_for_status(); cleaned=True
                    self.event(run_id,"cleanup",{"restored":True})
                except Exception as exc:
                    self.event(run_id,"cleanup",{"restored":False,"error":type(exc).__name__,"fallback":"independent fault TTL <=30s; sandbox retained through worker hard limit + fault TTL + margin"})
                    result["cleanup_pending_ttl"]=True
                    if final=="COMPLETED": final="FAILED"
                self.status(run_id,owner,final,result)
                if cleaned:
                    with self.sessions.begin() as db:
                        db.execute(update(SandboxLease).where(SandboxLease.id==settings().sandbox,SandboxLease.run_id==run_id).values(run_id=None,expires_at=0))
    async def execute(self,client,run_id,owner,cfg,rules):
        versions={}
        for name in ("gateway","order","payment","inventory"):
            response=await client.get(getattr(settings(),name)+"/health"); response.raise_for_status()
            versions[name]=response.json()
        self.event(run_id,"manifest",{"configuration":cfg.model_dump(),"seed":cfg.seed,"versions":versions,
            "engine_version":settings().version,"python":platform.python_version(),
            "image_identifiers":{name:versions[name].get("version") for name in versions},
            "reproduction":["Start the pinned Compose images", "Register/seed demo", "POST experiment run with a new idempotency key", "Inspect summary and state artifacts"],
            "nondeterminism":["OS scheduling", "database and network latency", "image tags are not content digests unless BUILD_VERSION is set to a digest"],
            "log_reference":{"execution_id":run_id,"source":"container JSON stdout"}})
        # Exclusive sandbox lease is held before destructive reset.
        response=await client.delete(settings().proxy_control+"/lease/"+run_id); response.raise_for_status()
        for name in ("order","payment","inventory"):
            response=await client.delete(getattr(settings(),name)+"/state"); response.raise_for_status()
        observer=Observer(client)
        baseline_key="baseline_"+run_id.replace("-","")
        fault_key="fault_"+run_id.replace("-","")
        async def workflow(key):
            body={"key":key,"amount":cfg.amount,"quantity":cfg.quantity}
            start=time.time()
            with trace.get_tracer("failurelab").start_as_current_span("checkout") as span:
                span.set_attribute("failurelab.execution_id",run_id)
                from opentelemetry.propagate import inject
                inject(client.headers)
                context=span.get_span_context()
                trace_reference={"trace_id":format(context.trace_id,"032x"),"span_id":format(context.span_id,"016x")}
                try:
                    response=await client.post(settings().gateway+"/checkout",json=body)
                    outcome={"status_code":response.status_code,"body":response.json()}
                except httpx.HTTPError as exc: outcome={"transport_error":type(exc).__name__}
            self.event(run_id,"workflow",{"trace_reference":trace_reference,"input":body,"outcome":outcome,"start":start,"end":time.time(),"execution_id":run_id})
            return outcome
        baseline_outcome=await workflow(baseline_key)
        if baseline_outcome.get("status_code")!=200: raise RuntimeError("baseline workflow failed")
        baseline,errors=await observer.snapshot(baseline_key)
        ref=self.event(run_id,"snapshot",{"stage":"baseline","key":baseline_key,"state":baseline,"errors":errors})
        baseline_results={key:evaluate(TypeAdapter(Rule).validate_python(rule),baseline,[ref]).model_dump() for key,rule in rules.items() if rule["kind"]!="transition"}
        self.event(run_id,"baseline_verification",{"evaluations":baseline_results})
        if errors or baseline.get("order",{}).get("status")!="finalized" or baseline.get("payment",{}).get("status")!="charged" or baseline.get("inventory",{}).get("status")!="reserved" or any(r["status"]!="PASS" for r in baseline_results.values()):
            raise RuntimeError("baseline observations/invariants did not pass; no fault finding generated")
        initial,errors=await observer.snapshot(fault_key)
        initial_ref=self.event(run_id,"snapshot",{"stage":"initial","key":fault_key,"state":initial,"errors":errors})
        response=await client.put(settings().proxy_control+"/lease",json={"execution_id":run_id,"fault":cfg.fault.model_dump()}); response.raise_for_status()
        self.event(run_id,"fault_schedule",{"activated_at":time.time(),"fault":cfg.fault.model_dump(),"lease":response.json()})
        await workflow(fault_key)
        response=await client.delete(settings().proxy_control+"/lease/"+run_id); response.raise_for_status()
        self.event(run_id,"fault_schedule",{"removed_at":time.time()})
        self.status(run_id,owner,"VERIFYING")
        end=time.monotonic()+cfg.consistency_seconds
        history={key:[] for key in rules}; refs=[initial_ref]; latest={}
        while True:
            observed,errors=await observer.snapshot(fault_key)
            ref=self.event(run_id,"snapshot",{"stage":"verification","key":fault_key,"state":observed,"errors":errors}); refs.append(ref)
            for key,rule in rules.items():
                evaluation=evaluate(TypeAdapter(Rule).validate_python(rule),observed,refs,initial)
                # Require all adapter observations, even for a vacuously true implication.
                if errors:
                    evaluation.status="INCONCLUSIVE"; evaluation.reason="missing authoritative observations: "+str(errors)
                history[key].append(evaluation.status); latest[key]=evaluation
            if time.monotonic()>=end: break
            await asyncio.sleep(min(cfg.retry_seconds,max(0,end-time.monotonic())))
        findings=[]
        for key,evaluation in latest.items():
            # A final gap in evidence cannot become a finding. A FAIL must persist
            # across the complete verification window; a prior PASS is convergence.
            if evaluation.status=="FAIL" and ("INCONCLUSIVE" in history[key] or "PASS" in history[key]):
                evaluation.status="INCONCLUSIVE"; evaluation.reason="observations were incomplete or unstable during consistency window"
            payload=evaluation.model_dump(); payload["invariant_id"]=key
            self.event(run_id,"evaluation",payload)
            if evaluation.status=="FAIL":
                with self.sessions() as db:
                    finding=Finding(run_id=run_id,invariant_id=key,summary="Cross-service correctness invariant violated",evidence=payload)
                    db.add(finding); db.commit(); findings.append(finding.id)
        return {"evaluations":{key:value.model_dump() for key,value in latest.items()},"finding_ids":findings,
                "baseline_key":baseline_key,"fault_key":fault_key}

async def recover(sessions=SessionLocal):
    """A lost worker is never blindly replayed over an uncertain transaction.
    Terminalize after deadline, clean the lease, retain snapshots for a fresh run.
    """
    now=time.time()
    with sessions() as db:
        stale=[(r.id,r.owner) for r in db.scalars(select(Run).where(Run.status.not_in(TERMINAL),Run.deadline<now))]
    for run_id,owner in stale:
        restored=False
        try:
            async with httpx.AsyncClient(timeout=2,trust_env=False,headers={"X-Control-Token":settings().control_token}) as client:
                response=await client.delete(settings().proxy_control+"/lease/"+run_id)
                restored=response.is_success
        except httpx.HTTPError: pass
        with sessions.begin() as db:
            row=db.get(Run,run_id)
            if row.status in TERMINAL: continue
            row.status="CANCELLED" if row.cancel_requested else "FAILED"
            row.result={"reason":"worker recovery: expired deadline","cleanup_confirmed":restored}
            row.updated_at=time.time()
            # Cleanup is not proof that the old worker stopped. Keep the fencing
            # lease until hard task limit + max fault TTL + margin. A cooperative
            # owner can release it after cancelling/awaiting all its work.
            row.result["sandbox_held_for_stale_worker"]=True
        Runner(sessions).event(run_id,"recovery",{"cleanup_confirmed":restored,"status":"expired","previous_owner":owner})
