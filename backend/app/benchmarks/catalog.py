from app.schemas.research import Scenario, Action
DEFECTS=['payment_ack_loss','unsafe_retry','lost_finalization','inventory_drift','concurrent_retry','failed_compensation']

def witness(defect):
    boundary={'payment_ack_loss':'charge','unsafe_retry':'charge','inventory_drift':'reserve','concurrent_retry':'charge','lost_finalization':'finalize','failed_compensation':'finalize'}[defect]
    actions=[Action(boundary=boundary,kind='http_503' if boundary=='finalize' else 'latency',phase='before' if boundary=='finalize' else 'after')]
    if defect=='failed_compensation': actions.append(Action(boundary='refund',kind='http_503',phase='before'))
    return Scenario(defect=defect,actions=actions,concurrency=2 if defect=='concurrent_retry' else 1)

def candidates(defects):
    out=[]
    for defect in sorted(set(defects)):
        base=witness(defect)
        out.append(base.model_copy(update={'actions':[]}))
        out.append(base)
        for kind,phase,delay,at in [('latency','after',30,0),('timeout','after',180,0),('http_503','before',0,0),('latency','after',180,350)]:
            actions=[base.actions[0].model_copy(update={'kind':kind,'phase':phase,'delay_ms':delay,'at_ms':at})]+base.actions[1:]
            out.append(base.model_copy(update={'actions':actions}))
    return out
