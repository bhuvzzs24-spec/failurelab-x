"""Runs only inside the restricted verification image, with no external network."""
import asyncio
import json
import tempfile
from pathlib import Path
from app.benchmarks.local import cluster
from app.benchmarks.executor import HTTPExecutor
from app.repair.patches import validate
from app.schemas.research import Scenario
from app.verification.counterfactual import compare

async def main():
    body=json.loads(Path('/input.json').read_text()); validate(body['source'])
    import hashlib
    from app.repair.patches import POLICY_PATH
    from app.schemas.research import VerificationReport
    runtime=POLICY_PATH.parent/'runtime.py'
    if hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest()!=body['base_sha256'] or (body.get('runtime_sha256') and hashlib.sha256(runtime.read_bytes()).hexdigest()!=body['runtime_sha256']):
        print(VerificationReport(outcome='INCONCLUSIVE',candidate_id=body['candidate_id'],reason='Verifier image differs from the recorded repair base or failing runtime. Rebuild the image and reproduce the source trial.').model_dump_json()); return
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp); (root/'app'/'benchmarks').mkdir(parents=True)
        # Copy trusted package, replacing only the validated literal policy file.
        import shutil, app
        shutil.copytree(Path(app.__file__).parent,root/'app',dirs_exist_ok=True)
        (root/'app'/'benchmarks'/'policies.py').write_text(body['source'])
        with cluster(root/'original') as (original_urls,original_token):
            with cluster(root/'candidate',{'PYTHONPATH':str(root)},package_root=root) as (candidate_urls,candidate_token):
                report=await compare(body['candidate_id'],Scenario.model_validate(body['scenario']),HTTPExecutor(original_urls,original_token),HTTPExecutor(candidate_urls,candidate_token))
                print(report.model_dump_json())
if __name__=='__main__':
    import signal
    signal.alarm(80) # independent container lifetime even if the host agent is killed
    asyncio.run(main())
