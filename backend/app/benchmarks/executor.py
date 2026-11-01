"""Collect authoritative observations before deterministic three-valued evaluation."""
import asyncio
import hashlib
import json
import time
import uuid
import httpx
from pydantic import TypeAdapter
from app.core.config import settings
from app.research.config import service_origins
from app.schemas.contracts import Rule
from app.invariants.engine import evaluate

RULES={
 'charged_order_finalized':('payment.amount','gte',1,'order.status','eq','finalized'),
 'finalized_payment_matches':('order.status','eq','finalized','payment.amount','eq','@order.amount'),
 'finalized_stock_matches':('order.status','eq','finalized','inventory.quantity','eq','@order.quantity'),
 'cancelled_payment_compensated':('order.status','eq','cancelled','payment.amount','eq',0),
 'cancelled_stock_released':('order.status','eq','cancelled','inventory.quantity','eq',0),
}
def operand(value): return {'path':value[1:]} if isinstance(value,str) and value.startswith('@') else {'value':value}
def rules():
    return {name:TypeAdapter(Rule).validate_python({'kind':'implies','antecedent':{'kind':'compare','left':{'path':a},'op':op,'right':operand(v)},'consequent':{'kind':'compare','left':{'path':b},'op':op2,'right':operand(v2)}}) for name,(a,op,v,b,op2,v2) in RULES.items()}

class HTTPExecutor:
    def __init__(self,urls=None,token=None):
        self.urls=urls or service_origins(); self.token=token or settings().control_token
    async def __call__(self,scenario,variant='original'):
        started=time.monotonic(); namespace=str(uuid.uuid4()); evidence={'execution_id':namespace,'scenario':scenario.model_dump(),'variant':variant,'correlation_id':uuid.uuid4().hex,'versions':{},'snapshots':[],'fault_receipts':[],'workflow':{},'adapter_errors':[],'nondeterminism':['OS scheduling','HTTP timeouts','database contention','process scheduling; seed controls selection only']}
        classification='INFRASTRUCTURE_ERROR'; signature=None
        async with httpx.AsyncClient(trust_env=False,headers={'X-Control-Token':self.token},timeout=6) as client:
            try:
                for role,url in self.urls.items():
                    response=await client.get(url+'/health'); response.raise_for_status(); evidence['versions'][role]=response.json()
                for role in ('order','payment','inventory'):
                    response=await client.delete(self.urls[role]+'/state/'+namespace); response.raise_for_status()
                response=await client.post(self.urls['gateway']+'/checkout',json={'namespace':namespace,'scenario':scenario.model_dump(),'variant':variant},headers={'X-Trace-Id':evidence['correlation_id']}); response.raise_for_status(); evidence['workflow']=response.json()
                # Drain bounded in-flight requests before the consistency window.
                await asyncio.sleep(.55 if scenario.actions else .05)
                deadline=time.monotonic()+scenario.consistency_ms/1000
                samples=[]
                while True:
                    state={}; receipts=[]; errors=[]
                    for role in ('order','payment','inventory'):
                        try:
                            response=await client.get(self.urls[role]+'/state/'+namespace); response.raise_for_status(); data=response.json()
                            value=data['state']
                            if not isinstance(value['status'],str) or type(value['amount']) is not int or type(value['quantity']) is not int: raise ValueError('invalid authoritative snapshot')
                            state[role]=value; receipts+=data['receipts']
                        except (httpx.HTTPError,KeyError,ValueError,TypeError): errors.append(role)
                    evaluations={name:evaluate(rule,state,[namespace+':snapshot:'+str(len(samples))]).model_dump() for name,rule in rules().items()}
                    if errors:
                        for result in evaluations.values(): result.update(status='INCONCLUSIVE',reason='missing authoritative adapters: '+','.join(errors))
                    samples.append({'state':state,'evaluations':evaluations,'adapter_errors':errors,'observed_at':time.time()}); evidence['fault_receipts']=receipts
                    if time.monotonic()>=deadline: break
                    await asyncio.sleep(.05)
                evidence['snapshots']=samples; evidence['adapter_errors']=sorted({r for sample in samples for r in sample['adapter_errors']})
                applied={r['action_index'] for r in evidence['fault_receipts']}
                stable_failures=[name for name in RULES if all(s['evaluations'][name]['status']=='FAIL' for s in samples)]
                final=samples[-1]['evaluations']
                if evidence['adapter_errors']: classification='INCONCLUSIVE'
                elif applied!=set(range(len(scenario.actions))): classification='INJECTION_NOT_OBSERVED'
                elif stable_failures:
                    classification='APPLICATION_VIOLATION'; signature=hashlib.sha256(json.dumps([scenario.defect,sorted(stable_failures)]).encode()).hexdigest()
                elif any(e['status']!='PASS' for e in final.values()): classification='INCONCLUSIVE'
                else: classification='NO_VIOLATION'
                evidence['violated_rules']=stable_failures
            except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
                evidence['infrastructure_error']=type(exc).__name__
            finally:
                cleanup=[]
                for role in ('order','payment','inventory'):
                    try:
                        response=await client.delete(self.urls[role]+'/state/'+namespace); response.raise_for_status()
                    except httpx.HTTPError: cleanup.append(role)
                evidence['cleanup_errors']=cleanup
        return {'id':str(uuid.uuid4()),'scenario':scenario.model_dump(),'variant':variant,'classification':classification,'signature':signature,'cost_seconds':time.monotonic()-started,'evidence':evidence}
