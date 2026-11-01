import os
import httpx
from app.research.config import local_origin
from app.schemas.research import VerificationReport

async def verify_isolated(candidate,scenario):
    origin=os.getenv('REPAIR_AGENT_URL')
    if not origin:
        return VerificationReport(outcome='INFRASTRUCTURE_ERROR',candidate_id=candidate.id,reason='Restricted Docker verification agent is not configured. Candidate code was not executed.',limitations=['Install Docker, build the verification image, and start the loopback sandbox agent.']).model_dump()
    url=local_origin(origin,{'127.0.0.1','localhost','repair-agent'})
    token=os.getenv('REPAIR_AGENT_TOKEN')
    if not token: return VerificationReport(outcome='INFRASTRUCTURE_ERROR',candidate_id=candidate.id,reason='Repair agent authentication not configured.').model_dump()
    try:
        async with httpx.AsyncClient(trust_env=False,timeout=100) as client:
            response=await client.post(url+'/verify',headers={'Authorization':'Bearer '+token},json={'candidate_id':candidate.id,'source':candidate.details['source'],'scenario':scenario.model_dump(),'base_sha256':candidate.details['base_sha256'],'runtime_sha256':candidate.details.get('runtime_sha256')}); response.raise_for_status()
            return VerificationReport.model_validate(response.json()).model_dump()
    except (httpx.HTTPError,ValueError):
        return VerificationReport(outcome='INFRASTRUCTURE_ERROR',candidate_id=candidate.id,reason='Restricted verification agent unavailable or returned an invalid report.').model_dump()
