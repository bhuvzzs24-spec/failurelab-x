"""Repeated-trial ddmin plus finite timing/input neighborhood reduction."""
import time
from app.schemas.research import MinimizeReport, Scenario

async def minimize(original,signature,execute,budget=20,repeats=2):
    attempts=[]; cost=0.0; used=0; current=original.model_copy(deep=True)
    async def preserves(candidate,stage):
        nonlocal used,cost
        candidate=Scenario.model_validate(candidate.model_dump())
        if used+repeats>budget: return None
        rows=[]
        for _ in range(repeats):
            trial=await execute(candidate); used+=1; cost+=trial['cost_seconds']; rows.append(trial)
        ok=all(r['classification']=='APPLICATION_VIOLATION' and r['signature']==signature for r in rows)
        attempts.append({'stage':stage,'scenario':candidate.model_dump(),'trial_ids':[r['id'] for r in rows],'classifications':[r['classification'] for r in rows],'matching':sum(r['signature']==signature and r['classification']=='APPLICATION_VIOLATION' for r in rows),'repeats':repeats,'accepted':ok})
        if any(r['classification'] in ('INCONCLUSIVE','INFRASTRUCTURE_ERROR','INJECTION_NOT_OBSERVED') for r in rows): return None
        return ok
    if not await preserves(current,'confirm_original'):
        return MinimizeReport(original=original,reduced=original,removed_events=[],attempts=attempts,signature=signature,reproductions=attempts[-1]['matching'] if attempts else 0,confirmation_trials=repeats if attempts else 0,local_minimality_tested=False,cost_seconds=cost,limitations=['Original failure did not reproduce consistently; no reduction accepted.'])
    # ddmin complements; with <=2 faults this still handles the empty sequence.
    n=2
    while current.actions:
        length=len(current.actions); chunk=max(1,(length+n-1)//n); changed=False
        for start in range(0,length,chunk):
            candidate=current.model_copy(update={'actions':current.actions[:start]+current.actions[start+chunk:]})
            if await preserves(candidate,'ddmin_remove'):
                current=candidate; n=max(2,n-1); changed=True; break
        if changed: continue
        if n>=length: break
        n=min(length,n*2)
    # Reduce to tested lattice values, restarting after each accepted reduction.
    def neighbors(value):
        for i,action in enumerate(value.actions):
            for field in ('delay_ms','at_ms','max_hits'):
                if field=='delay_ms' and action.kind!='latency': continue # timeout is fixed at 500ms; 503 has no delay
                minimum=1 if field=='max_hits' else 0
                for amount in sorted({minimum,max(minimum,getattr(action,field)//2)}):
                    if amount>=getattr(action,field): continue
                    actions=list(value.actions); actions[i]=action.model_copy(update={field:amount})
                    yield value.model_copy(update={'actions':actions})
        for field in ('amount','quantity','concurrency'):
            if getattr(value,field)>1: yield value.model_copy(update={field:1})
    changed=True
    while changed and used+repeats<=budget:
        changed=False
        for candidate in neighbors(current):
            if await preserves(candidate,'parameter_reduce'):
                current=candidate; changed=True; break
    # Explicitly audit single removals and lattice neighbors; budget exhaustion is not minimality.
    audit=[current.model_copy(update={'actions':current.actions[:i]+current.actions[i+1:]}) for i in range(len(current.actions))]+list(neighbors(current))
    local=True
    for candidate in audit:
        outcome=await preserves(candidate,'local_audit')
        if outcome is None or outcome: local=False
    confirmations=0; matches=0
    if used+repeats<=budget:
        confirmed=await preserves(current,'final_confirmation'); confirmations=repeats; matches=attempts[-1]['matching']
        if confirmed is not True: local=False
    else: local=False
    remaining=list(current.actions); removed=[]
    for action in original.actions:
        if action in remaining: remaining.remove(action)
        elif not any(a.boundary==action.boundary and a.kind==action.kind and a.phase==action.phase for a in current.actions): removed.append(action)
    return MinimizeReport(original=original,reduced=current,removed_events=removed,attempts=attempts,signature=signature,reproductions=matches,confirmation_trials=confirmations,local_minimality_tested=local,cost_seconds=cost,limitations=['Locality covers single fault deletions and the reported finite parameter lattice only.','Repeated success is empirical; scheduling, timeout and database nondeterminism remain.','Budget includes every replay, including inconclusive and infrastructure outcomes.'])
