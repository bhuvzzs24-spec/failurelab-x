"""Paired interventions, with no probabilistic causality claims."""
from app.schemas.research import Hypothesis

async def investigate(scenario,signature,execute,budget=20,repeats=2):
    hypotheses=[]; used=0
    interventions=[('acknowledgement','Lost payment acknowledgement','payment',lambda s:s.model_copy(update={'actions':[a for a in s.actions if not (a.boundary=='charge' and a.phase=='after')]})),('retry','Retry after a lost charge acknowledgement creates duplicate ledger entries','payment',lambda s:s.model_copy(update={'actions':[a for a in s.actions if a.boundary!='charge']})),('concurrency','Concurrent charge delivery contributes to the violation','payment',lambda s:s.model_copy(update={'concurrency':1})),('finalization','Order finalization failed','order',lambda s:s.model_copy(update={'actions':[a for a in s.actions if a.boundary!='finalize']})),('compensation','Compensation acknowledgement or execution failed','payment',lambda s:s.model_copy(update={'actions':[a for a in s.actions if a.boundary!='refund']})),('reservation','Reservation retry changed authoritative stock','inventory',lambda s:s.model_copy(update={'actions':[a for a in s.actions if a.boundary!='reserve']}))]
    for identity,description,service,remove in interventions:
        control=remove(scenario)
        h=Hypothesis(id=identity,description=description,services=[service,'order'],assumptions=['Fresh isolated state for each member of each pair.','Other workflow inputs and program version held fixed.','Fault receipts establish delivered interventions.'],intervention='Compare recorded failure scenario with suspected mechanism removed.')
        if identity=='retry' and scenario.defect!='unsafe_retry':
            h.status='INCONCLUSIVE'; h.contradicting_observations=['The selected program variant does not implement the unsafe payment retry under test. Fault removal alone cannot establish that explanation.']; hypotheses.append(h); continue
        if control==scenario:
            h.status='INCONCLUSIVE'; h.contradicting_observations=['No corresponding controllable action in this scenario.']; hypotheses.append(h); continue
        if used+2*repeats>budget:
            h.status='INCONCLUSIVE'; h.contradicting_observations=['Intervention budget exhausted.']; hypotheses.append(h); continue
        pairs=[]
        for _ in range(repeats):
            introduced=await execute(scenario); removed=await execute(control); used+=2
            pairs.append((introduced,removed)); h.outcomes.append({'introduced_trial_id':introduced['id'],'removed_trial_id':removed['id'],'introduced':introduced['classification'],'removed':removed['classification'],'same_signature_introduced':introduced['signature']==signature,'removed_signature':removed['signature']})
        valid=all(a['classification']=='APPLICATION_VIOLATION' and a['signature']==signature and b['classification'] in ('NO_VIOLATION','APPLICATION_VIOLATION') for a,b in pairs)
        if valid and all(b['classification']=='NO_VIOLATION' for a,b in pairs):
            h.status='SUPPORTED'; h.supporting_observations=[p['removed_trial_id'] for p in h.outcomes]
        elif valid and all(b['signature']==signature for a,b in pairs):
            h.status='REFUTED'; h.contradicting_observations=[p['removed_trial_id'] for p in h.outcomes]
        else: h.status='INCONCLUSIVE'
        hypotheses.append(h)
    return {'hypotheses':[h.model_dump() for h in hypotheses],'executed':used,'interpretation':'Supported denotes the observed paired effect in this controlled benchmark, not a unique root cause or proof of causality.','provider':'deterministic'}
