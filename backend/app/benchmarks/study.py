"""Leakage-separated finite synthetic benchmark. No novelty or superiority claim.

All strategies see the same training catalogue. Evaluation cases are never fed
back to any planner. The cohort order rotates to reduce systematic warm-up bias.
Full observations are persisted by the injected executor, reports retain references.
"""
import hashlib
import json
import statistics
from pathlib import Path
from app.benchmarks.catalog import candidates,witness
from app.schemas.research import Action
from app.planning.search import search
from app.minimization.reduce import minimize
from app.verification.counterfactual import compare

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def held_out(defect):
    s=witness(defect)
    return s.model_copy(update={'amount':37,'quantity':3,'actions':[a.model_copy(update={'delay_ms':275}) if a.kind=='latency' else a for a in s.actions]})
def compact_verification(report,label):
    return {'control':label,'outcome':report.outcome,'cases':[{'name':c['name'],'original_trial_id':c['original']['id'],'comparison_trial_id':c['candidate']['id'],'original':c['original']['classification'],'comparison':c['candidate']['classification'],'wall_delta_seconds':c['wall_overhead_seconds'],'gateway_cpu_delta_seconds':c.get('gateway_cpu_overhead_seconds')} for c in report.cases],'limitations':report.limitations}

async def study(config,execute,record,graph=None,invariants=None):
    train=candidates(config.search.defects);holdouts=[held_out(d) for d in sorted(set(config.search.defects))]
    training_keys={s.model_dump_json() for s in train}
    if any(s.model_dump_json() in training_keys for s in holdouts):raise ValueError('held-out scenario overlaps training catalogue')
    root=Path(__file__).resolve().parents[1]
    protocol={'id':'failurelab-synthetic-v2','training_sha256':digest([s.model_dump() for s in train]),'held_out_sha256':digest([s.model_dump() for s in holdouts]),'held_out_scope':'unseen inputs and latency parameters; same seeded program families','no_history':True,'alpha':1.4,'seeded_synthetic_defects':True,'novel_discoveries_claimed':False,'implementation_hashes':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['planning/search.py','benchmarks/catalog.py','benchmarks/study.py','benchmarks/runtime.py','invariants/engine.py']}}
    all_trials=[];phase='discovery'
    async def run(s,variant='original'):
        row=await execute(s,variant);all_trials.append((phase,row));return row
    comparisons=[];order=[]
    strategies=['random','coverage','adaptive']
    for index,seed in enumerate(config.seeds):
        rotated=strategies[index%3:]+strategies[:index%3]
        for strategy in rotated:
            order.append({'seed':seed,'strategy':strategy})
            selection=config.search.model_copy(update={'seed':seed,'strategy':strategy})
            def decision(step,s,score,context,reward,trial):
                record(step,s,score,{**context,'seed':seed,'phase':'discovery','cohort_index':len(order)-1},reward,trial)
            comparisons.append(await search(selection,run,decision,graph,invariants,history=[]))
    phase='witness_controls';references=[]
    for defect in sorted(set(config.search.defects)):
        s=witness(defect);original=await run(s);repeat=await run(s);fixed=await run(s,'reference');baseline=await run(s.model_copy(update={'actions':[],'concurrency':1}))
        references.append({'defect':defect,'original_trial_id':original['id'],'repeat_trial_id':repeat['id'],'reference_trial_id':fixed['id'],'baseline_trial_id':baseline['id'],'original':original['classification'],'reference':fixed['classification'],'baseline':baseline['classification'],'repeat_matches_signature':original['classification']=='APPLICATION_VIOLATION' and repeat['classification']=='APPLICATION_VIOLATION' and original['signature']==repeat['signature'],'reference_wall_delta_seconds':fixed['cost_seconds']-original['cost_seconds']})
    phase='held_out_evaluation';evaluation=[]
    for s in holdouts:
        for repetition in range(config.repeats):
            original=await run(s);fixed=await run(s,'reference')
            evaluation.append({'defect':s.defect,'scenario':s.model_dump(),'repetition':repetition,'original_trial_id':original['id'],'reference_trial_id':fixed['id'],'original':original['classification'],'reference':fixed['classification'],'wall_delta_seconds':fixed['cost_seconds']-original['cost_seconds']})
    phase='comparator_controls';control=witness(sorted(set(config.search.defects))[0])
    async def original(s):return await run(s)
    async def reference(s):return await run(s,'reference')
    good=compact_verification(await compare('shipped-reference-control',control,original,reference),'trusted reference recovery')
    bad=compact_verification(await compare('unmodified-negative-control',control,original,original),'unmodified vulnerable implementation')
    phase='minimization_control';reduction_case=control.model_copy(deep=True)
    if len(reduction_case.actions)<2:
        boundary='charge' if reduction_case.actions[0].boundary=='reserve' else 'reserve'
        reduction_case.actions.append(Action(boundary=boundary,kind='latency',phase='before',delay_ms=10))
    measured=await run(reduction_case)
    reduction=None
    if measured['classification']=='APPLICATION_VIOLATION':reduction=(await minimize(reduction_case,measured['signature'],run,min(config.budget,40),config.repeats)).model_dump()
    means={s:statistics.mean(r['unique_bugs'] for r in comparisons if r['strategy']==s) for s in strategies}
    samples={s:[r['unique_bugs'] for r in comparisons if r['strategy']==s] for s in strategies}
    unknown={'INCONCLUSIVE','INFRASTRUCTURE_ERROR','INJECTION_NOT_OBSERVED'}
    comparator_conclusive=good['outcome'] not in ('INCONCLUSIVE','INFRASTRUCTURE_ERROR') and bad['outcome'] not in ('INCONCLUSIVE','INFRASTRUCTURE_ERROR')
    counts={p:sum(1 for name,row in all_trials if name==p) for p in sorted({p for p,r in all_trials})}
    return {'protocol':protocol,'cohort_order':order,'comparisons':comparisons,'mean_unique_bugs':means,'sample_stddev_unique_bugs':{s:statistics.stdev(values) for s,values in samples.items()},'adaptive_improved_observed_mean':means['adaptive']>max(means['random'],means['coverage']),'seeds':config.seeds,'budget_per_strategy_per_seed':config.search.budget,'reference_comparisons':references,'reference_comparison_note':'Shipped reference controls, not generated candidate verification.','held_out_evaluation':evaluation,'held_out_executed':len(evaluation)*2,'witness_reproduction_matches':sum(r['repeat_matches_signature'] for r in references),'witness_pairs':len(references),'unexpected_control_violations':sum(r[v]=='APPLICATION_VIOLATION' for r in references for v in ('reference','baseline'))+sum(r['reference']=='APPLICATION_VIOLATION' for r in evaluation),'adjudicated_false_positive_findings':None,'comparator_controls':[good,bad],'comparator_control_accuracy':(int(good['outcome']=='PATCH_PASSES_TESTED_SCENARIOS')+int(bad['outcome']=='PATCH_FAILS_VERIFICATION'))/2 if comparator_conclusive else None,'comparator_accuracy_scope':'Two known shipped controls only; not general verification accuracy.','minimization_control':reduction,'trial_counts_by_phase':counts,'total_executed_trials':len(all_trials),'total_trial_wall_seconds':sum(r['cost_seconds'] for p,r in all_trials),'classification_counts':{c:sum(r['classification']==c for p,r in all_trials) for c in sorted({r['classification'] for p,r in all_trials})},'environment':all_trials[0][1]['evidence'].get('versions',{}) if all_trials else {},'candidate_repair_verification_success':None,'limitations':['Known seeded synthetic defects; no novel bug discovery claim.','Held-outs share defect families and are never used for planner updates.','Small repeated seed set; no statistical superiority claim.','Unadjudicated findings do not establish a global false-positive rate.','Generated candidate accuracy requires isolated Docker verification.','Wall costs include controlled waits; gateway CPU is not full-system CPU/memory overhead.']}
