"""Independent verifier: matched cases, immutable original failure and held-outs."""
from app.schemas.research import Scenario, VerificationReport
from app.benchmarks.catalog import witness

async def compare(candidate_id,scenario,original_executor,candidate_executor):
    cases=[('original_failure',scenario),('repeat_failure',scenario),('regression_no_fault',scenario.model_copy(update={'actions':[],'concurrency':1})),('heldout_inputs',scenario.model_copy(update={'amount':37,'quantity':3})),('heldout_timing',scenario.model_copy(update={'actions':[a.model_copy(update={'delay_ms':min(500,a.delay_ms+90)}) for a in scenario.actions]})),('related_concurrency',scenario.model_copy(update={'concurrency':2}))]
    report=[]
    for name,case in cases:
        original=await original_executor(case); patched=await candidate_executor(case)
        original_cpu=original['evidence'].get('workflow',{}).get('gateway_cpu_seconds')
        candidate_cpu=patched['evidence'].get('workflow',{}).get('gateway_cpu_seconds')
        cpu_delta=candidate_cpu-original_cpu if isinstance(candidate_cpu,(int,float)) and isinstance(original_cpu,(int,float)) else None
        report.append({'gateway_cpu_overhead_seconds':cpu_delta,'name':name,'scenario':case.model_dump(),'original':original,'candidate':patched,'wall_overhead_seconds':patched['cost_seconds']-original['cost_seconds']})
    uncertainty={'INCONCLUSIVE','INFRASTRUCTURE_ERROR','INJECTION_NOT_OBSERVED'}
    if any(r[v]['classification']=='INFRASTRUCTURE_ERROR' for r in report for v in ('original','candidate')): outcome='INFRASTRUCTURE_ERROR'
    elif any(r[v]['classification'] in uncertainty for r in report for v in ('original','candidate')): outcome='INCONCLUSIVE'
    elif report[0]['original']['classification']!='APPLICATION_VIOLATION' or report[1]['original']['signature']!=report[0]['original']['signature']: outcome='INCONCLUSIVE'
    elif any(r['candidate']['classification']!='NO_VIOLATION' for r in report): outcome='PATCH_FAILS_VERIFICATION'
    else: outcome='PATCH_PASSES_TESTED_SCENARIOS'
    return VerificationReport(outcome=outcome,candidate_id=candidate_id,cases=report,environment={'original_versions':report[0]['original']['evidence'].get('versions',{}),'candidate_versions':report[0]['candidate']['evidence'].get('versions',{})},limitations=['Finite benchmark scenarios do not prove absence of bugs.','Held-outs are fixed independent verification cases, not random samples of all possible failures.','Wall and gateway process CPU time are measured; full-system resource overhead is not measured.','Timeouts and process scheduling remain nondeterministic.'])
