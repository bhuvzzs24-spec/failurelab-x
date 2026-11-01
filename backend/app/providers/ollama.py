"""Optional, local-only structured proposals. Evidence IDs must already exist."""
import os
from pydantic import BaseModel, ConfigDict, Field
import httpx
from app.research.config import local_origin
from app.benchmarks.catalog import DEFECTS
class Proposal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    description:str=Field(min_length=1,max_length=1000)
    evidence_ids:list[str]=Field(max_length=10)
    policy_defect:str|None=None
class Proposals(BaseModel):
    model_config=ConfigDict(extra='forbid')
    proposals:list[Proposal]=Field(max_length=5)
async def propose(evidence_ids,summary):
    origin=os.getenv('OLLAMA_URL')
    if not origin: return {'status':'DISABLED','proposals':[]}
    url=local_origin(origin,{'127.0.0.1','localhost','ollama'})
    try:
        async with httpx.AsyncClient(trust_env=False,timeout=30) as client:
            response=await client.post(url+'/api/chat',json={'model':os.getenv('OLLAMA_MODEL','qwen3:8b'),'stream':False,'format':Proposals.model_json_schema(),'messages':[{'role':'system','content':'Propose hypotheses or one policy repair. Use only supplied evidence IDs. Do not assert truth, confidence, test results, or source execution. Return JSON.'},{'role':'user','content':__import__('json').dumps({'evidence_ids':evidence_ids,'observations':summary})}]}); response.raise_for_status()
            if len(response.content)>65536: raise ValueError('model output exceeds limit')
            result=Proposals.model_validate_json(response.json()['message']['content'])
            if any(not set(p.evidence_ids)<=set(evidence_ids) or (p.policy_defect is not None and p.policy_defect not in DEFECTS) for p in result.proposals): raise ValueError('unrecognized proposal references')
            return {'status':'PROPOSALS_ONLY','proposals':result.model_dump()['proposals'],'warning':'Unverified model suggestions; invariant truth and causal status are determined experimentally.'}
    except (httpx.HTTPError,ValueError,KeyError): return {'status':'UNAVAILABLE_OR_INVALID','proposals':[]}
