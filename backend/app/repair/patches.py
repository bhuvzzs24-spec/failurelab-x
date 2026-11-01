"""A deliberately constrained, auditable repair surface. Never executes patches."""
import ast
import difflib
import hashlib
import os
import tempfile
from pathlib import Path
from app.benchmarks.catalog import DEFECTS

POLICY_PATH=Path(__file__).resolve().parents[1]/'benchmarks'/'policies.py'

def validate(source):
    if len(source.encode())>10000: raise ValueError('patch too large')
    tree=ast.parse(source)
    statements=[n for n in tree.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))]
    if len(statements)!=1 or not isinstance(statements[0],ast.Assign): raise ValueError('only a literal policy assignment is supported')
    assignment=statements[0]
    if len(assignment.targets)!=1 or not isinstance(assignment.targets[0],ast.Name) or assignment.targets[0].id!='POLICIES': raise ValueError('POLICIES assignment required')
    value=ast.literal_eval(assignment.value)
    if not isinstance(value,dict) or set(value)!=set(DEFECTS) or any(type(v) is not bool for v in value.values()): raise ValueError('exact boolean policy map required')
    return value

def prepare(defect,source=None):
    original=POLICY_PATH.read_text(); original_map=validate(original)
    values={**original_map,defect:True}
    candidate=source or '"""Candidate policy repair; execute only in the verification container."""\nPOLICIES = '+repr(values)+'\n'
    changed=validate(candidate)
    if changed==original_map: raise ValueError('candidate changes no policy')
    # Operator-controlled workspace root; user requests cannot select paths.
    root=Path(os.getenv('REPAIR_WORKSPACE_ROOT',tempfile.gettempdir()+'/failurelab-repairs')); root.mkdir(mode=0o700,parents=True,exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='candidate-',dir=root)); os.chmod(folder,0o700)
    (folder/'policies.py').write_text(candidate); (folder/'original.py').write_text(original)
    patch=''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),fromfile='a/backend/app/benchmarks/policies.py',tofile='b/backend/app/benchmarks/policies.py'))
    return patch,{'source':candidate,'base_sha256':hashlib.sha256(original.encode()).hexdigest(),'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'workspace_id':folder.name,'supported_path':'backend/app/benchmarks/policies.py','explanation':'Enable bounded idempotent recovery for '+defect,'checks':{'syntax':'PASS','literal_policy_static_analysis':'PASS','execution_tests':'NOT_RUN; isolated verifier required'},'limitations':['Constrained benchmark policy repair only; no arbitrary repository patching.','No merge or deployment performed.']}
