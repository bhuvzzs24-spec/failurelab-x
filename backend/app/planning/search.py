"""Cost-aware contextual linear UCB with equal-space reproducible baselines.

A ridge model learns novelty reward from context. UCB is an acquisition utility,
not calibrated confidence. Actual time normalizes estimated candidate cost.
No third-party numerical framework is required for these small matrices.
"""
import math
import random
import time
from app.benchmarks.catalog import candidates, DEFECTS

def features(scenario,graph=None,invariants=None):
    graph=graph or {}; nodes=graph.get('nodes',[]); edges=graph.get('edges',[])
    services={n['id']:n['name'] for n in nodes}
    boundaries={'charge':'payment','refund':'payment','reserve':'inventory','finalize':'order'}
    targets={boundaries[a.boundary] for a in scenario.actions}
    degrees=sum(1 for e in edges if services.get(e.get('target_id')) in targets)
    relevance=sum(1 for r in invariants or [] if any(name+'.' in str(r) for name in targets))
    return [1.0]+[float(scenario.defect==d) for d in DEFECTS]+[float(any(a.kind==k for a in scenario.actions)) for k in ('latency','timeout','http_503')]+[len(scenario.actions)/2,scenario.concurrency/2,max([a.delay_ms for a in scenario.actions]+[0])/500,min(degrees,6)/6,min(relevance,6)/6]

def solve(matrix,vector):
    # Gaussian elimination with partial pivoting. A=I+sum(xx^T) is positive definite.
    n=len(vector); a=[list(row)+[vector[i]] for i,row in enumerate(matrix)]
    for col in range(n):
        pivot=max(range(col,n),key=lambda r:abs(a[r][col])); a[col],a[pivot]=a[pivot],a[col]
        divisor=a[col][col]
        for j in range(col,n+1): a[col][j]/=divisor
        for row in range(n):
            if row==col: continue
            scale=a[row][col]
            for j in range(col,n+1): a[row][j]-=scale*a[col][j]
    return [row[-1] for row in a]

class Planner:
    def __init__(self,config,graph=None,invariants=None,history=None):
        self.config=config; self.rng=random.Random(config.seed); self.space=candidates(config.defects)
        self.graph=graph; self.invariants=invariants; self.counts={}; self.covered=set(); self.seen=set()
        size=len(features(self.space[0])); self.a=[[float(i==j) for j in range(size)] for i in range(size)]; self.b=[0.0]*size; self.costs={}
        for row in history or []: self.update(row['scenario'],row['signature'],row['cost_seconds'],row['classification'])
    def choose(self):
        scores=[]; theta=solve(self.a,self.b)
        for index,s in enumerate(self.space):
            x=features(s,self.graph,self.invariants); key=s.model_dump_json()
            if self.config.strategy=='random': score=self.rng.random()
            elif self.config.strategy=='coverage':
                atoms=self.atoms(s); score=len(atoms-self.covered)+1/(1+self.counts.get(key,0))+self.rng.random()*.01
            else:
                uncertainty=math.sqrt(max(0,sum(v*w for v,w in zip(x,solve(self.a,x)))))
                estimate=sum(v*w for v,w in zip(theta,x))
                predicted_cost=self.costs.get(s.defect,.85+sum(a.delay_ms for a in s.actions)/1000)
                score=(estimate+1.4*uncertainty)/(max(.1,predicted_cost)) + self.rng.random()*1e-6
            scores.append((score,index,x))
        score,index,x=max(scores); return self.space[index],score,{'features':x,'coverage_size':len(self.covered),'unique_signatures':len(self.seen),'candidate_count':len(self.space),'score_interpretation':'acquisition utility; not probability','strategy':self.config.strategy}
    def atoms(self,s): return {s.defect+':'+a.boundary+':'+a.kind+':'+a.phase+':'+str(a.delay_ms)+':'+str(a.at_ms) for a in s.actions}|{s.defect+':concurrency:'+str(s.concurrency)}
    def update(self,scenario,signature,cost,classification):
        from app.schemas.research import Scenario
        if isinstance(scenario,dict): scenario=Scenario.model_validate(scenario)
        reward=float(classification=='APPLICATION_VIOLATION' and signature not in self.seen)
        if classification=='APPLICATION_VIOLATION': self.seen.add(signature)
        x=features(scenario,self.graph,self.invariants)
        for i in range(len(x)):
            self.b[i]+=reward*x[i]
            for j in range(len(x)): self.a[i][j]+=x[i]*x[j]
        key=scenario.model_dump_json(); self.counts[key]=self.counts.get(key,0)+1; self.covered|=self.atoms(scenario)
        self.costs[scenario.defect]=.5*self.costs.get(scenario.defect,cost)+.5*cost
        return reward

async def search(config,execute,record,graph=None,invariants=None,history=None):
    planner=Planner(config,graph,invariants,history); trials=[]; first=None; discovered=set(); families=set()
    for step in range(config.budget):
        scenario,score,context=planner.choose(); trial=await execute(scenario)
        reward=planner.update(scenario,trial['signature'],trial['cost_seconds'],trial['classification'])
        if trial['classification']=='APPLICATION_VIOLATION':
            discovered.add(trial['signature']); families.add(scenario.defect)
            if first is None: first=step+1
        record(step,scenario,score,context,reward,trial)
        trials.append(trial)
    return {'strategy':config.strategy,'seed':config.seed,'budget':config.budget,'executed':len(trials),'unique_bugs':len(families),'unique_violation_signatures':len(discovered),'experiments_until_first_finding':first,'execution_cost_seconds':sum(t['cost_seconds'] for t in trials),'classification_counts':{c:sum(t['classification']==c for t in trials) for c in sorted({t['classification'] for t in trials})},'trial_ids':[t['id'] for t in trials],'false_positive_findings':None,'false_positive_note':'Requires independent oracle adjudication; not inferred from invariant failures.'}
