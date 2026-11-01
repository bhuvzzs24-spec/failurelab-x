import pytest
from app.benchmarks.catalog import candidates,DEFECTS
from app.benchmarks.study import held_out,study
from app.schemas.research import ResearchCreate,SearchInput

def test_holdouts_do_not_overlap_training():
    space={s.model_dump_json() for s in candidates(DEFECTS)}
    assert all(held_out(d).model_dump_json() not in space for d in DEFECTS)

async def test_study_equal_budget_no_evaluation_feedback():
    rows=[];decisions=[]
    async def execute(s,variant='original'):
        row={'id':str(len(rows)),'scenario':s.model_dump(),'variant':variant,'classification':'NO_VIOLATION','signature':None,'cost_seconds':.01,'evidence':{'versions':{'gateway':{'version':'unit fixture'}},'workflow':{'gateway_cpu_seconds':.001}}};rows.append(row);return row
    config=ResearchCreate(kind='BENCHMARK',idempotency_key='unit',search=SearchInput(budget=2,defects=['payment_ack_loss']),seeds=[17,42],budget=2)
    report=await study(config,execute,lambda *args:decisions.append(args))
    assert len(report['comparisons'])==6 and all(c['executed']==2 for c in report['comparisons'])
    assert len(decisions)==12 # held-out/control/minimization results never train a planner
    assert report['trial_counts_by_phase']['discovery']==12
    assert report['held_out_executed']==4
    assert report['candidate_repair_verification_success'] is None
    assert report['comparator_control_accuracy'] is None
    assert report['protocol']['seeded_synthetic_defects'] and not report['protocol']['novel_discoveries_claimed']
    assert report['cohort_order'][0]['strategy']!=report['cohort_order'][3]['strategy']
